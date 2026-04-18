import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentAPI } from '../services/api';

interface ChunkPreview {
  index: number;
  content: string;
  char_count: number;
}

interface PreviewResult {
  chunks: ChunkPreview[];
  total_chunks: number;
  total_chars: number;
  avg_chunk_size: number;
  params: {
    max_chunk_size: number;
    min_chunk_size: number;
    overlap_size: number;
  };
  filename?: string;
  file_size?: number;
}

export default function Knowledge() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [maxChunkSize, setMaxChunkSize] = useState(500);
  const [minChunkSize, setMinChunkSize] = useState(50);
  const [overlapSize, setOverlapSize] = useState(50);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setTitle(selectedFile.name);
      setPreview(null);
      setError('');
      setSuccess('');
    }
  };

  const handlePreview = async () => {
    if (!file) {
      setError('请先选择文件');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('max_chunk_size', maxChunkSize.toString());
      formData.append('min_chunk_size', minChunkSize.toString());
      formData.append('overlap_size', overlapSize.toString());

      const response = await documentAPI.previewUpload(formData);
      setPreview(response.data.data);
    } catch (err: any) {
      setError(err.response?.data?.message || '预览失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('请先选择文件');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      formData.append('max_chunk_size', maxChunkSize.toString());
      formData.append('min_chunk_size', minChunkSize.toString());
      formData.append('overlap_size', overlapSize.toString());

      const response = await documentAPI.upload(formData);

      // 检查响应状态
      if (response.data.code === 200) {
        setSuccess('文档上传成功！');

        // 重置表单
        setFile(null);
        setTitle('');
        setPreview(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        // 后端返回了错误码
        setError(response.data.message || '上传失败');
      }
    } catch (err: any) {
      console.error('Upload error:', err);

      // 尝试多种方式获取错误信息
      const errorMessage =
        err.response?.data?.message ||
        err.response?.data?.error ||
        err.message ||
        '上传失败';

      setError(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

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
              className="text-blue-600 font-medium"
            >
              知识库管理
            </button>
            <button
              onClick={handleLogout}
              className="btn-secondary"
            >
              退出登录
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 左侧：上传和参数设置 */}
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-bold text-gray-800 mb-4">上传文档</h2>

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

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择文件
                  </label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.doc,.docx"
                    onChange={handleFileSelect}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    支持格式：PDF、TXT、DOC、DOCX
                  </p>
                </div>

                {file && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      文档标题
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="input-field"
                      placeholder="请输入文档标题"
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <h2 className="text-xl font-bold text-gray-800 mb-4">分段参数</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    最大分段大小：{maxChunkSize} 字符
                  </label>
                  <input
                    type="range"
                    min="200"
                    max="2000"
                    step="100"
                    value={maxChunkSize}
                    onChange={(e) => setMaxChunkSize(Number(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    最小分段大小：{minChunkSize} 字符
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="200"
                    step="10"
                    value={minChunkSize}
                    onChange={(e) => setMinChunkSize(Number(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    重叠大小：{overlapSize} 字符
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    step="10"
                    value={overlapSize}
                    onChange={(e) => setOverlapSize(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <button
                  onClick={handlePreview}
                  disabled={!file || loading}
                  className="btn-secondary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '预览中...' : '预览分段'}
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!file || uploading}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? '上传中...' : '确认上传'}
                </button>
              </div>
            </div>
          </div>

          {/* 右侧：预览区域 */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-800 mb-4">分段预览</h2>

            {!preview ? (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>选择文件并点击"预览分段"查看效果</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 统计信息 */}
                <div className="bg-blue-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">总分段数</p>
                    <p className="text-2xl font-bold text-blue-600">{preview.total_chunks}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">平均大小</p>
                    <p className="text-2xl font-bold text-blue-600">{preview.avg_chunk_size}</p>
                  </div>
                </div>

                {/* 分段列表 */}
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {preview.chunks.map((chunk) => (
                    <div key={chunk.index} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-600">
                          分段 #{chunk.index + 1}
                        </span>
                        <span className="text-xs text-gray-500">
                          {chunk.char_count} 字符
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
