import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function Prompts() {
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const username = localStorage.getItem('username') || '用户';

  useEffect(() => {
    fetchPrompt();
  }, []);

  const fetchPrompt = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/prompts/rag');
      const promptContent = response.data.data.content;
      setContent(promptContent);
      setOriginalContent(promptContent);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载提示词失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!content.trim()) {
      setError('提示词内容不能为空');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.put('/prompts/rag', { content });
      setOriginalContent(content);
      setSuccess('提示词保存成功！新对话将使用更新后的提示词。');
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('确认重置为系统默认提示词？当前修改将丢失。')) return;
    setResetting(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/prompts/rag/reset');
      const resetContent = response.data.data.content;
      setContent(resetContent);
      setOriginalContent(resetContent);
      setSuccess('已重置为默认提示词。');
    } catch (err: any) {
      setError(err.response?.data?.message || '重置失败');
    } finally {
      setResetting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  const isChanged = content !== originalContent;

  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            智能问答系统
          </h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/chat')}
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              智能问答
            </button>
            <button
              onClick={() => navigate('/knowledge')}
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              知识库管理
            </button>
            <button className="text-blue-600 font-medium">
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

      {/* 主内容区 */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-gray-800">RAG问答系统提示词</h2>
              <p className="text-sm text-gray-500 mt-1">
                修改对话系统的系统提示词模板，影响AI回答的风格和约束。支持变量：
                <code className="bg-gray-100 px-1 rounded text-xs mx-1">{'{input}'}</code>（用户提问）、
                <code className="bg-gray-100 px-1 rounded text-xs mx-1">{'{context}'}</code>（检索到的参考资料）
              </p>
            </div>
            {isChanged && (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full font-medium">
                未保存
              </span>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
              {success}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12 text-gray-500">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
              加载中...
            </div>
          ) : (
            <>
              <textarea
                value={content}
                onChange={(e) => {
                  setContent(e.target.value);
                  setSuccess('');
                }}
                rows={20}
                className="w-full border border-gray-300 rounded-lg p-4 font-mono text-sm text-gray-800 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 resize-y"
                placeholder="请输入系统提示词..."
              />

              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleSave}
                  disabled={saving || !isChanged}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? '保存中...' : '保存提示词'}
                </button>
                <button
                  onClick={handleReset}
                  disabled={resetting}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed px-6"
                >
                  {resetting ? '重置中...' : '恢复默认'}
                </button>
                <button
                  onClick={() => {
                    setContent(originalContent);
                    setSuccess('');
                    setError('');
                  }}
                  disabled={!isChanged}
                  className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed px-6"
                >
                  取消修改
                </button>
              </div>
            </>
          )}
        </div>

        {/* 使用说明 */}
        <div className="card mt-6">
          <h3 className="text-base font-semibold text-gray-700 mb-3">使用说明</h3>
          <ul className="text-sm text-gray-600 space-y-2">
            <li>• 提示词是对话系统的"系统指令"，定义AI的角色、约束和回答风格</li>
            <li>• 变量 <code className="bg-gray-100 px-1 rounded">{'{input}'}</code> 会被替换为用户的实际问题</li>
            <li>• 变量 <code className="bg-gray-100 px-1 rounded">{'{context}'}</code> 会被替换为从知识库检索到的参考资料</li>
            <li>• 修改后立即生效，新发起的对话将使用新的提示词</li>
            <li>• 若提示词不合适，可点击"恢复默认"重置为系统内置提示词</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
