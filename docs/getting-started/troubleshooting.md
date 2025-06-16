# Troubleshooting Guide

Having issues with Open Karaoke Studio? This guide covers the most common problems and their solutions.

## 🚨 Quick Fixes

### Application Won't Start

**Backend won't start:**
```bash
# Check Python virtual environment
source backend/venv/bin/activate  # Linux/macOS
# or: backend\venv\Scripts\activate  # Windows

# Verify dependencies
pip install -r backend/requirements.txt

# Check for port conflicts
lsof -i :5000  # See what's using port 5000
```

**Frontend won't start:**
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install

# Try different port if 5173 is taken
pnpm dev --port 3001
```

### Can't Access the Application

**Backend not responding (http://localhost:5000):**
- Check if backend is running: `ps aux | grep python`
- Look for error messages in terminal
- Try restarting: `Ctrl+C` then `./run_api.sh`

**Frontend not loading (http://localhost:5173):**
- Check browser console for errors (F12)
- Try different browser (Chrome recommended)
- Clear browser cache and reload

## 🔧 Installation Issues

### Python/Backend Problems

**"python: command not found"**
```bash
# On macOS/Linux, try:
python3 --version

# On Windows, verify Python installation
python --version

# If not installed, download from python.org
```

**"pip: command not found"**
```bash
# Usually comes with Python, but if missing:
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

**Virtual environment issues:**
```bash
# Delete and recreate virtual environment
rm -rf backend/venv
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

**"Module not found" errors:**
```bash
# Ensure virtual environment is activated
source backend/venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt

# For development dependencies
pip install -r requirements-test.txt
```

### Node.js/Frontend Problems

**"node: command not found"**
- Download and install Node.js from [nodejs.org](https://nodejs.org)
- Verify installation: `node --version`

**"pnpm: command not found"**
```bash
# Install pnpm globally
npm install -g pnpm

# Or use npm instead (less efficient)
npm install  # instead of pnpm install
```

**Dependency installation fails:**
```bash
# Clear cache and retry
pnpm store prune
rm -rf node_modules pnpm-lock.yaml
pnpm install

# If still failing, try npm
npm install
```

## 🎵 Audio Processing Issues

### Processing Never Completes

**Check system resources:**
```bash
# Monitor CPU and memory usage
top  # Linux/macOS
# Task Manager on Windows

# Check available disk space
df -h  # Linux/macOS
```

**Look at backend logs:**
```bash
# View recent logs
tail -f backend/logs/app.log

# Look for error patterns
grep ERROR backend/logs/app.log
```

**Common solutions:**
- Restart backend service
- Try smaller audio file (< 10MB)
- Ensure sufficient disk space (at least 2GB free)
- Close other applications to free memory

### Poor Separation Quality

**Try different songs:**
- Start with popular rock/pop songs
- Avoid live recordings or acoustic tracks
- Use studio recordings for best results

**Check GPU acceleration:**
```bash
# Test if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# Should print: True (if you have GPU and CUDA installed)
```

**Audio format issues:**
- Convert to MP3 or WAV format
- Ensure file isn't corrupted
- Try downloading from different source

### Processing Errors

**"Out of memory" errors:**
```bash
# Check available RAM
free -h  # Linux
# Activity Monitor on macOS
# Task Manager on Windows

# Solutions:
# 1. Close other applications
# 2. Try smaller files
# 3. Add more RAM if possible
```

**"Permission denied" errors:**
```bash
# Fix file permissions (Linux/macOS)
chmod 755 backend/run_api.sh
chmod 755 backend/run_celery.sh

# Check directory permissions
ls -la backend/
```

## 🌐 Network & API Issues

### YouTube Import Failing

**Update yt-dlp:**
```bash
cd backend
source venv/bin/activate
pip install --upgrade yt-dlp
```

**Check YouTube URL format:**
- Use full YouTube URLs: `https://www.youtube.com/watch?v=VIDEO_ID`
- Avoid playlist URLs
- Try different videos if one fails

**Network connectivity:**
```bash
# Test internet connection
curl -I https://www.youtube.com
# Should return HTTP 200 OK
```

### API Connection Issues

**Frontend can't reach backend:**
```bash
# Test backend API directly
curl http://localhost:5000/api/songs
# Should return: {"songs": []}

# Check if backend is running on correct port
netstat -tulpn | grep :5000  # Linux
lsof -i :5000  # macOS
```

**CORS errors in browser:**
- Check browser console (F12)
- Restart both frontend and backend
- Verify backend has Flask-CORS installed

## 🗄️ Database Issues

### Database Errors

**"Database locked" errors:**
```bash
# Stop all processes using the database
pkill -f "python.*main.py"
pkill -f celery

# Remove lock files
rm -f backend/karaoke.db-wal backend/karaoke.db-shm

# Restart backend
cd backend && ./run_api.sh
```

**Database corruption:**
```bash
# Backup current database
cp backend/karaoke.db backend/karaoke.db.backup

# Reset database (loses all songs!)
rm backend/karaoke.db
cd backend
alembic upgrade head
```

**Migration errors:**
```bash
# Check current migration state
cd backend
alembic current

# Reset and upgrade
alembic downgrade base
alembic upgrade head
```

## 🔍 Performance Issues

### Slow Processing

**Enable GPU acceleration:**
```bash
# Check GPU availability
nvidia-smi  # Should show GPU info

# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Optimize for CPU:**
```bash
# Set environment variables for better CPU performance
export OMP_NUM_THREADS=4  # Adjust based on CPU cores
export MKL_NUM_THREADS=4
```

**System optimization:**
- Close unnecessary applications
- Ensure adequate cooling (CPU throttling)
- Use SSD for faster file operations

### Memory Issues

**Monitor memory usage:**
```bash
# Check memory usage during processing
watch -n 1 'free -h'  # Linux
# Activity Monitor on macOS
```

**Reduce memory usage:**
```bash
# Process smaller chunks
# Edit backend/app/config.py
# Reduce DEMUCS_DEVICE memory allocation
```

## 🛠️ Development Issues

### Code Changes Not Applying

**Backend changes:**
```bash
# Restart backend server
Ctrl+C  # Stop current server
./run_api.sh  # Restart
```

**Frontend changes:**
```bash
# Frontend auto-reloads, but if not:
Ctrl+C  # Stop dev server
pnpm dev  # Restart
```

**Clear caches:**
```bash
# Backend
rm -rf backend/__pycache__
rm -rf backend/app/__pycache__

# Frontend
rm -rf frontend/.vite
```

### Testing Issues

**Tests failing:**
```bash
# Run tests with verbose output
cd backend
python -m pytest -v

# Run specific test
python -m pytest tests/test_specific.py -v
```

## 📋 Getting Help

### Gathering Debug Information

When reporting issues, include:

1. **System information:**
   ```bash
   # Operating system
   uname -a  # Linux/macOS
   
   # Python version
   python --version
   
   # Node.js version  
   node --version
   ```

2. **Error logs:**
   ```bash
   # Backend logs
   tail -50 backend/logs/app.log
   
   # Browser console errors (F12 in browser)
   ```

3. **Steps to reproduce:**
   - What you were trying to do
   - What you expected to happen
   - What actually happened

### Where to Get Help

**Documentation:**
- [User Guide](../user-guide/README.md) - Complete feature documentation
- [API Documentation](../api/README.md) - For developers
- [Development Guide](../development/README.md) - For contributors

**Community Support:**
- [GitHub Issues](https://github.com/yourusername/open-karaoke/issues) - Bug reports and questions
- [Discussions](https://github.com/yourusername/open-karaoke/discussions) - General questions

**Before Asking:**
1. Search existing issues for your problem
2. Try the solutions in this troubleshooting guide
3. Include debug information in your report

## ✅ Prevention Tips

### Avoid Common Issues

**Regular maintenance:**
```bash
# Update dependencies monthly
cd backend && pip install --upgrade -r requirements.txt
cd frontend && pnpm update

# Clean up old files
rm -rf backend/logs/*.log.old
rm -rf frontend/.vite
```

**Backup your data:**
```bash
# Backup database and library
cp backend/karaoke.db backup/
cp -r karaoke_library backup/
```

**Monitor system health:**
- Keep adequate free disk space (>2GB)
- Monitor CPU and memory usage
- Update operating system regularly

---

**Still having issues?** 
- 🐛 [Report a Bug](../development/contributing/issue-reporting.md)
- 💬 [Ask a Question](https://github.com/yourusername/open-karaoke/discussions)
- 📖 [Check User Guide](../user-guide/README.md)
