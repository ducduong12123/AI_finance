# Deploy lên Railway

## Bước 1: Chuẩn bị

### 1.1 Tạo tài khoản Railway
- Truy cập https://railway.app
- Đăng nhập bằng GitHub

### 1.2 Push code lên GitHub
```bash
# Từ thư mục gốc dự án
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

## Bước 2: Deploy Backend

### 2.1 Tạo project mới trên Railway
1. Click "New Project"
2. Chọn "Deploy from GitHub repo"
3. Chọn repo `AI_finance`

### 2.2 Cấu hình Environment Variables
Trong Railway Dashboard → Variables, thêm:

```
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
CORS_ORIGINS=https://your-frontend-url.vercel.app,http://localhost:3000
```

### 2.3 Settings
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- **Healthcheck Path**: `/health`

## Bước 3: Deploy Frontend (Vercel - Recommended)

### 3.1 Push frontend code riêng (optional)
Nếu muốn deploy frontend riêng:
```bash
cd frontend
git init
git add .
git commit -m "Frontend init"
# Tạo repo mới trên GitHub cho frontend
git push origin main
```

### 3.2 Deploy lên Vercel
1. Truy cập https://vercel.com
2. Import repo frontend
3. Set Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-backend.up.railway.app
   ```

### 3.3 Update CORS
Sau khi có URL frontend, update `CORS_ORIGINS` trong Railway:
```
CORS_ORIGINS=https://your-frontend.vercel.app
```

## Bước 4: Kiểm tra

### 4.1 Test API
```bash
curl https://your-railway-backend.up.railway.app/health
```

### 4.2 Test chat endpoint
```bash
curl -X POST https://your-railway-backend.up.railway.app/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "giá VCB", "session_id": "test123"}'
```

## Troubleshooting

### Lỗi 1: Module not found
```
Error: No module named 'src'
```
**Fix**: Đảm bảo cấu trúc thư mục đúng và `__init__.py` tồn tại

### Lỗi 2: Port already in use
```
Error: Address already in use
```
**Fix**: Railway tự động set `$PORT`, không hardcode port

### Lỗi 3: CORS error
**Fix**: Update `CORS_ORIGINS` với domain frontend chính xác

### Lỗi 4: vnstock API fail
**Fix**: vnstock cần network access, Railway hỗ trợ tốt

## Cấu trúc files quan trọng

```
├── railway.json      # Railway config
├── nixpacks.toml     # Build config
├── Procfile          # Process definition
├── runtime.txt       # Python version
└── requirements.txt  # Dependencies
```

## Monitoring

Railway cung cấp:
- Logs real-time
- Metrics (CPU, Memory)
- Deploy history
- Auto-restart on failure

## Cost

Railway free tier:
- 500 hours runtime/month
- 1GB RAM
- Shared CPU
- Custom domains

Nếu vượt quá, upgrade lên Hobby ($5/month)
