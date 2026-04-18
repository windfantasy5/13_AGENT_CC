@echo off
echo ========================================
echo Quick Test Guide
echo ========================================
echo.

echo This guide will help you test the fixes:
echo.

echo [Test 1] Document Preview
echo 1. Start backend: start_backend.bat
echo 2. Start frontend: start_frontend.bat
echo 3. Login to the system
echo 4. Click "知识库管理" in top navigation
echo 5. Upload a document (PDF, TXT, DOC, DOCX)
echo 6. Adjust chunk parameters if needed
echo 7. Click "预览分段" button
echo 8. Verify: You should see all chunks displayed
echo.

echo [Test 2] Multi-round Conversation
echo 1. Click "智能问答" in top navigation
echo 2. Click "+ 新建对话" to create a conversation
echo 3. Send first question and wait for response
echo 4. Send second question
echo 5. Verify: Second question displays correctly
echo 6. Verify: System responds to second question
echo 7. Send third question to confirm
echo.

echo [Test 3] Streaming Response with RAG
echo 1. Make sure you have uploaded documents
echo 2. In chat page, ask a question related to your documents
echo 3. Verify: You see "📚 参考资料" cards appear first
echo 4. Verify: AI response streams word by word
echo 5. Verify: After completion, reference cards disappear
echo 6. Verify: Only AI answer remains
echo.

echo [Test 4] Streaming Response without RAG
echo 1. Ask a general question not in your documents
echo 2. Verify: No reference cards appear
echo 3. Verify: AI response streams normally
echo.

echo ========================================
echo Press any key to exit...
pause >nul
