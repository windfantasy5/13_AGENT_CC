import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 认证API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),

  register: (username: string, password: string, email: string) =>
    api.post('/auth/register', { username, password, email }),
};

// 对话API
export const chatAPI = {
  createConversation: (title?: string) =>
    api.post('/chat/conversations', { title }),

  getConversations: (page = 1, pageSize = 20) =>
    api.get('/chat/conversations', { params: { page, page_size: pageSize } }),

  getConversation: (id: number) =>
    api.get(`/chat/conversations/${id}`),

  deleteConversation: (id: number) =>
    api.delete(`/chat/conversations/${id}`),

  deleteAllConversations: () =>
    api.delete('/chat/conversations'),

  sendMessage: (conversationId: number, content: string, useRag = true) =>
    api.post('/chat/message', { conversation_id: conversationId, content, use_rag: useRag }),

  sendMessageStream: (conversationId: number, content: string, useRag = true) => {
    const token = localStorage.getItem('token');
    const url = `${API_BASE_URL}/chat/message/stream`;

    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        content,
        use_rag: useRag,
      }),
    });
  },
};

// 文档API
export const documentAPI = {
  previewUpload: (formData: FormData) => {
    return api.post('/documents/preview-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  upload: (formData: FormData, onProgress?: (progress: number) => void) => {
    return api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },

  uploadDocument: (file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },

  getDocuments: (page = 1, pageSize = 20) =>
    api.get('/documents', { params: { page, page_size: pageSize } }),

  deleteDocument: (id: number) =>
    api.delete(`/documents/${id}`),
};

// 知识库API
export const knowledgeAPI = {
  search: (query: string, topK = 5, documentId?: number) =>
    api.post('/knowledge/search', { query, top_k: topK, document_id: documentId }),
};

export default api;
