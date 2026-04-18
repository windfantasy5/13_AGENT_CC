import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatAPI } from '../services/api';
import type { Conversation, Message } from '../types';

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const username = localStorage.getItem('username') || '用户';

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await chatAPI.getConversations();
      setConversations(response.data.data.items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id: number) => {
    try {
      const response = await chatAPI.getConversation(id);
      const conv = response.data.data;
      setCurrentConversation(conv);
      setMessages(conv.messages || []);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await chatAPI.createConversation();
      const newConv = response.data.data;
      await loadConversations();
      setCurrentConversation({ ...newConv, message_count: 0, updated_at: newConv.created_at });
      setMessages([]);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentConversation || loading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setLoading(true);

    const tempUserMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      // 尝试使用流式API
      const response = await chatAPI.sendMessageStream(currentConversation.id, userMessage);

      if (!response.ok) {
        console.error('Stream API failed, falling back to regular API');
        // 降级到普通API
        const fallbackResponse = await chatAPI.sendMessage(currentConversation.id, userMessage);
        const { user_message, assistant_message } = fallbackResponse.data.data;

        setMessages((prev) => [
          ...prev.filter((m) => m.id !== tempUserMsg.id),
          {
            id: user_message.id,
            role: 'user',
            content: user_message.content,
            created_at: user_message.created_at,
          },
          {
            id: assistant_message.id,
            role: 'assistant',
            content: assistant_message.content,
            tokens: assistant_message.tokens,
            model: assistant_message.model,
            created_at: assistant_message.created_at,
          },
        ]);

        await loadConversations();
        setLoading(false);
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let buffer = '';
      let assistantContent = '';
      let ragContextMsg: Message | null = null;
      const tempAssistantId = Date.now() + 1;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();

            if (data === '[DONE]') {
              // 移除RAG上下文
              if (ragContextMsg) {
                setMessages((prev) => prev.filter(m => m.id !== ragContextMsg!.id));
              }
              continue;
            }

            if (!data) continue;

            try {
              const chunk = JSON.parse(data);

              if (chunk.type === 'user_message') {
                setMessages((prev) =>
                  prev.map((m) => m.id === tempUserMsg.id ? { ...m, id: chunk.data.id } : m)
                );
              } else if (chunk.type === 'rag_context') {
                const ragContent = chunk.data.results
                  .map((r: any, i: number) =>
                    `📚 参考资料 ${i + 1} (相似度: ${(r.score * 100).toFixed(1)}%)\n来源: ${r.document_title}\n\n${r.content}`
                  )
                  .join('\n\n---\n\n');

                ragContextMsg = {
                  id: tempAssistantId - 1,
                  role: 'assistant',
                  content: ragContent,
                  created_at: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, ragContextMsg!]);
              } else if (chunk.type === 'assistant_chunk') {
                assistantContent += chunk.data.content;

                setMessages((prev) => {
                  const existing = prev.find(m => m.id === tempAssistantId);
                  if (existing) {
                    return prev.map(m =>
                      m.id === tempAssistantId
                        ? { ...m, content: assistantContent }
                        : m
                    );
                  } else {
                    return [...prev, {
                      id: tempAssistantId,
                      role: 'assistant',
                      content: assistantContent,
                      created_at: new Date().toISOString(),
                    }];
                  }
                });
              } else if (chunk.type === 'assistant_message') {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === tempAssistantId
                      ? {
                          id: chunk.data.id,
                          role: 'assistant',
                          content: chunk.data.content,
                          tokens: chunk.data.tokens,
                          model: chunk.data.model,
                          created_at: chunk.data.created_at,
                        }
                      : m
                  )
                );
              } else if (chunk.type === 'error') {
                throw new Error(chunk.content);
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e, 'data:', data);
            }
          }
        }
      }

      await loadConversations();
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('发送消息失败: ' + (error as Error).message);
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
    }
  };

  const deleteConversation = async (id: number) => {
    if (!confirm('确定要删除这个对话吗？')) return;

    try {
      await chatAPI.deleteConversation(id);
      await loadConversations();
      if (currentConversation?.id === id) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const exportConversation = async (id: number, title: string) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://127.0.0.1:8000/api/v1/chat/conversations/${id}/export`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/plain'
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('导出失败:', response.status, errorText);
        throw new Error(`导出失败: ${response.status}`);
      }

      // 获取文件内容
      const blob = await response.blob();

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      // 从响应头获取文件名，如果没有则使用默认名称
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `对话_${title}_${new Date().toISOString().split('T')[0]}.txt`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = decodeURIComponent(filenameMatch[1]);
        }
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      console.log('导出成功:', filename);
    } catch (error) {
      console.error('Failed to export conversation:', error);
      alert('导出失败: ' + (error as Error).message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            智能问答系统
          </h1>
          <div className="flex items-center gap-4">
            <button className="text-blue-600 font-medium">
              智能问答
            </button>
            <button
              onClick={() => navigate('/knowledge')}
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              知识库管理
            </button>
            <button
              onClick={() => navigate('/prompts')}
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              提示词设置
            </button>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                {username[0].toUpperCase()}
              </div>
              <span className="font-medium text-gray-800">{username}</span>
            </div>
            <button onClick={handleLogout} className="btn-secondary">
              退出登录
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 bg-white border-r border-gray-200 flex flex-col overflow-hidden`}>
          <div className="p-4 border-b border-gray-200">
            <button onClick={createNewConversation} className="btn-primary w-full text-sm">
              + 新建对话
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => loadConversation(conv.id)}
                className={`p-3 rounded-lg cursor-pointer transition-all ${
                  currentConversation?.id === conv.id
                    ? 'bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-blue-500'
                    : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 truncate">{conv.title}</p>
                    <p className="text-xs text-gray-500">{conv.message_count} 条消息</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        exportConversation(conv.id, conv.title);
                      }}
                      className="text-gray-400 hover:text-blue-500"
                      title="导出对话"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="text-gray-400 hover:text-red-500"
                      title="删除对话"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-500 hover:text-gray-700">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {currentConversation?.title || '选择或创建一个对话'}
              </h2>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && !currentConversation && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-4">
                  <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-800 mb-2">欢迎使用智能问答系统</h3>
                <p className="text-gray-600 max-w-md">开始新对话或选择现有对话继续与AI助手交流</p>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={msg.id || index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} fade-in`}>
                <div className={msg.role === 'user' ? 'message-user' : 'message-assistant'}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.model && (
                    <p className="text-xs opacity-70 mt-2">
                      {msg.model} • {msg.tokens} tokens
                    </p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start fade-in">
                <div className="message-assistant">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-indicator"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-indicator" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full typing-indicator" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          {currentConversation && (
            <div className="bg-white border-t border-gray-200 p-4">
              <div className="max-w-4xl mx-auto">
                <div className="flex space-x-3">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="在这里输入您的问题..."
                    className="input-field flex-1 resize-none"
                    rows={3}
                    disabled={loading}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={loading || !inputMessage.trim()}
                    className="btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
