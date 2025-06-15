# Installation Guide

This guide will walk you through setting up Open Karaoke Studio from scratch. Follow these steps to get both the backend and frontend running locally.

## 📋 Prerequisites

Before starting, ensure you have these installed:

### Required Software
- **Node.js** 16+ ([Download](https://nodejs.org/))
- **Python** 3.8+ ([Download](https://python.org/))
- **pnpm** ([Install Guide](https://pnpm.io/installation))
- **Git** ([Download](https://git-scm.com/))

### Optional (for better performance)
- **Redis** ([Installation Guide](https://redis.io/download)) - For background job processing
- **FFmpeg** ([Download](https://ffmpeg.org/)) - For advanced audio processing
- **CUDA** ([Installation Guide](https://developer.nvidia.com/cuda-downloads)) - For GPU acceleration

## 🚀 Quick Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/open-karaoke-studio.git
cd open-karaoke-studio
```

### Step 2: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or on Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Initialize database
alembic upgrade head
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install Node.js dependencies
pnpm install
```

### Step 4: Start the Application

Open two terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # If not already activated
./run_api.sh
# or manually: python app/main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```

### Step 5: Access the Application

- **Frontend**: Open http://localhost:5173
- **Backend API**: Available at http://localhost:5000

🎉 **You're ready to go!** → [Process Your First Song](first-song.md)

## 📦 Detailed Installation

### Backend Detailed Setup

#### 1. Python Environment
```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.8+
```

#### 2. Install Dependencies
```bash
# Install all requirements
pip install -r requirements.txt

# For development with testing
pip install -r requirements-test.txt
```

#### 3. Database Setup
```bash
# Run database migrations
alembic upgrade head

# Verify database was created
ls -la karaoke.db  # Should exist
```

#### 4. Configuration (Optional)
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

#### 5. Test Backend
```bash
# Start the API server
./run_api.sh

# Test in another terminal
curl http://localhost:5000/api/songs
# Should return: {"songs": []}
```

### Frontend Detailed Setup

#### 1. Node.js Environment
```bash
cd frontend

# Verify Node.js version
node --version  # Should be 16+

# Verify pnpm installation
pnpm --version
```

#### 2. Install Dependencies
```bash
# Install all packages
pnpm install

# Verify installation
pnpm list  # Shows installed packages
```

#### 3. Development Configuration
```bash
# The frontend is pre-configured to work with backend on localhost:5000
# No additional configuration needed for development
```

#### 4. Test Frontend
```bash
# Start development server
pnpm dev

# Should show:
# Local:   http://localhost:5173/
# Network: use --host to expose
```

## ⚙️ Optional Enhancements

### Enable Background Jobs (Recommended)
```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server

# Start Celery worker (in separate terminal)
cd backend
source venv/bin/activate
./run_celery.sh
```

### GPU Acceleration Setup
```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# If False and you have an NVIDIA GPU:
# 1. Install CUDA toolkit from nvidia.com
# 2. Reinstall PyTorch with CUDA support:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Development Tools
```bash
# Backend development tools
cd backend
pip install pytest black flake8

# Frontend development tools
cd frontend
pnpm add -D eslint prettier @types/node
```

## 🐳 Docker Installation (Alternative)

If you prefer Docker:

```bash
# Build and start all services
docker-compose up --build

# Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:5000
```

## 🔧 Troubleshooting

### Common Issues

**Python "command not found"**
- Install Python from python.org
- On macOS: Use `python3` instead of `python`

**pnpm not found**
- Install with: `npm install -g pnpm`
- Or use npm: `npm install` (less efficient)

**Port already in use**
- Backend: Change port in `backend/app/config.py`
- Frontend: Use `pnpm dev --port 3001`

**Module not found errors**
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

**Permission denied (Linux/macOS)**
- Use `chmod +x run_api.sh run_celery.sh`

### Performance Issues

**Slow audio processing**
- Install CUDA for GPU acceleration
- Close other applications to free RAM
- Use smaller audio files for testing

**Frontend slow to load**
- Clear browser cache
- Restart development server
- Check network connection

### Getting Help

If you're still having issues:

1. **Check the logs**:
   ```bash
   # Backend logs
   tail -f backend/logs/app.log
   
   # Frontend console
   # Open browser developer tools
   ```

2. **Verify system requirements** - Review [System Requirements](README.md#system-requirements)

3. **Search existing issues** - Check GitHub issues for solutions

4. **Ask for help** - Create a new issue with:
   - Your operating system
   - Python and Node.js versions
   - Complete error messages
   - Steps you've tried

## ✅ Verification Checklist

After installation, verify everything works:

- [ ] Backend starts without errors (`./run_api.sh`)
- [ ] Frontend loads in browser (`http://localhost:5173`)
- [ ] Can access song library (empty list is OK)
- [ ] No console errors in browser developer tools
- [ ] Backend API responds (`curl http://localhost:5000/api/songs`)

## 🎯 Next Steps

**Installation complete!** Now you're ready to:

1. **[Process Your First Song](first-song.md)** - Learn the basic workflow
2. **[Explore Features](../user-guide/README.md)** - Discover all capabilities
3. **[Configure Advanced Features](../deployment/configuration.md)** - Optimize your setup

---

**Need Help?** 
- 💬 [Troubleshooting Guide](troubleshooting.md)
- 🐛 [Report Installation Issues](../development/contributing/issue-reporting.md)
- 📚 [Development Setup](../development/setup/README.md) (for contributors)
