# 🚀 HVLC_DB Auto-Run System

This guide shows you how to automatically start your entire HVLC_DB system with a single command.

## 🎯 Quick Start

### Option 1: Bash Script (Recommended)
```bash
./auto_start.sh
```

### Option 2: Python Launcher (Auto-opens browser)
```bash
python quick_auto_start.py
```

## ✨ What Auto-Run Does

1. **🔧 Starts API Server** on port 5001
2. **🎨 Starts Frontend** on port 5173 
3. **🤖 Checks Ollama** (local & homelab)
4. **🧪 Tests All Systems** 
5. **🌐 Opens Browser** (Python launcher only)
6. **📊 Shows Status** and keeps services running
7. **🛑 Clean Shutdown** when you press Ctrl+C

## 📋 System Status

Once running, you'll see:
```
✅ API Server: http://localhost:5001
✅ Frontend: http://localhost:5173
📝 Logs Directory: ./logs
```

## 🎯 Quick Actions

| Action | Command |
|--------|---------|
| **Open UI** | http://localhost:5173 |
| **Test API** | `curl http://localhost:5001/api/health` |
| **View Logs** | `tail -f logs/*.log` |
| **Stop All** | Press `Ctrl+C` |

## 🔧 Troubleshooting

### Port Conflicts
- Script automatically kills processes on ports 5001 & 5173
- Handles macOS AirPlay (port 5000) conflicts

### Dependencies
- **Python**: Required for API server
- **Node.js**: Required for frontend
- **Ollama**: Optional (checks both local & homelab)

### Log Files
All service logs are saved in `./logs/`:
- `api_server.log` - API server output
- `frontend.log` - Frontend development server output

## 🚦 Service Health Checks

The script continuously monitors:
- ✅ API server health endpoint
- ✅ Frontend accessibility  
- ✅ AI chat functionality
- ✅ Database connectivity

## 🎉 Success Indicators

When everything is working:
1. **Green checkmarks** for all services
2. **AI chat test passes**
3. **Browser opens to working UI**
4. **Ada responds to messages**

## 💡 Pro Tips

- **First time?** Script auto-installs frontend dependencies
- **Development?** Hot-reload works for both frontend and backend
- **Multiple sessions?** Each run gets its own log files
- **Clean shutdown?** Always use Ctrl+C for proper cleanup

---

**🎯 Goal:** One command to rule them all - `./auto_start.sh` and you're ready to analyze data with Ada! 