const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Use ANGLE D3D11 backend - more stable on Windows while keeping WebGL working
// This fixes "GPU state invalid after WaitForGetOffsetInRange" error
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('enable-features', 'Vulkan');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

let mainWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1920,
        height: 1080,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false, // For simple IPC/Socket.IO usage
        },
        backgroundColor: '#000000',
        frame: false, // Frameless for custom UI
        titleBarStyle: 'hidden',
        show: false, // Don't show until ready
    });

    // In dev, load Vite server. In prod, load index.html
    const isDev = process.env.NODE_ENV !== 'production';

    const loadFrontend = (retries = 3) => {
        const url = isDev ? 'http://localhost:5173' : null;
        const loadPromise = isDev
            ? mainWindow.loadURL(url)
            : mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));

        loadPromise
            .then(() => {
                console.log('Frontend loaded successfully!');
                windowWasShown = true;
                mainWindow.show();
                if (isDev) {
                    mainWindow.webContents.openDevTools();
                }
            })
            .catch((err) => {
                console.error(`Failed to load frontend: ${err.message}`);
                if (retries > 0) {
                    console.log(`Retrying in 1 second... (${retries} retries left)`);
                    setTimeout(() => loadFrontend(retries - 1), 1000);
                } else {
                    console.error('Failed to load frontend after all retries. Keeping window open.');
                    windowWasShown = true;
                    mainWindow.show(); // Show anyway so user sees something
                }
            });
    };

    loadFrontend();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonBackend() {
    const backendDir = path.join(__dirname, '../backend');
    const projectRoot = path.join(__dirname, '..');
    const scriptPath = path.join(backendDir, 'server.py');
    
    // Determine the python executable path
    let pythonExe = 'python'; // Default fallback
    
    const venvPath = process.platform === 'win32' 
        ? path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
        : path.join(projectRoot, '.venv', 'bin', 'python');
    
    const fs = require('fs');
    if (fs.existsSync(venvPath)) {
        pythonExe = venvPath;
        console.log(`[MAIN] Using virtual environment python: ${pythonExe}`);
    } else {
        console.log(`[MAIN] Virtual environment not found at ${venvPath}, falling back to system 'python'`);
    }

    console.log(`[MAIN] Starting Python backend: ${pythonExe} ${scriptPath}`);

    pythonProcess = spawn(pythonExe, [scriptPath], {
        cwd: backendDir,
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    console.log(`[MAIN] Python backend spawned with PID: ${pythonProcess.pid}`);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error]: ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[MAIN] Python backend exited with code ${code}`);
        if (code !== 0 && !isRelaunching) {
            console.log('[MAIN] Backend crashed unexpectedly. Attempting to restart in 2 seconds...');
            setTimeout(startPythonBackend, 2000);
        }
        pythonProcess = null; // Clear reference
    });

    pythonProcess.on('error', (err) => {
        console.error(`[MAIN] Failed to start Python backend: ${err}`);
        // If it failed and we weren't already trying 'py', try 'py' as a last resort on Windows
        if (process.platform === 'win32' && pythonExe !== 'py') {
            console.log('[MAIN] Attempting fallback to "py" launcher...');
            pythonExe = 'py';
            pythonProcess = spawn(pythonExe, [scriptPath], { 
                cwd: backendDir,
                env: { ...process.env, PYTHONUNBUFFERED: '1' }
            });
            
            pythonProcess.stdout.on('data', (data) => console.log(`[Python]: ${data.toString().trim()}`));
            pythonProcess.stderr.on('data', (data) => console.error(`[Python Error]: ${data.toString().trim()}`));
            pythonProcess.on('close', (code) => {
                console.log(`[MAIN] Python backend (fallback) exited with code ${code}`);
                pythonProcess = null;
            });
        }
    });
}

app.whenReady().then(() => {
    ipcMain.on('window-minimize', () => {
        if (mainWindow) mainWindow.minimize();
    });

    ipcMain.on('window-maximize', () => {
        if (mainWindow) {
            if (mainWindow.isMaximized()) {
                mainWindow.unmaximize();
            } else {
                mainWindow.maximize();
            }
        }
    });

    ipcMain.on('window-close', () => {
        if (mainWindow) mainWindow.close();
    });

let isRelaunching = false;
    ipcMain.on('relaunch-app', () => {
        if (isRelaunching) return;
        isRelaunching = true;
        console.log('[MAIN] Relaunching app requested via IPC...');
        
        // Pass a flag to the new instance to indicate it's a relaunch
        // Using app.getPath('exe') as the first argument is often more reliable
        const args = process.argv.slice(1).filter(arg => arg !== '--relaunch').concat(['--relaunch']);
        console.log(`[MAIN] Relaunching with args: ${args.join(' ')}`);
        
        try {
            // It's often safer to use the absolute path to the executable when relaunching
            app.relaunch({ 
                executablePath: process.argv[0],
                args: args
            });
            console.log('[MAIN] Relaunch scheduled.');
        } catch (err) {
            console.error('[MAIN] Error during app.relaunch:', err);
        }
        
        // Give it a tiny bit of time to ensure relaunch is registered by the OS before we quit
        setTimeout(() => {
            console.log('[MAIN] Quitting now for relaunch...');
            app.quit();
        }, 500); // Increased delay
    });

    const isRelaunch = process.argv.includes('--relaunch');
    checkBackendPort(8000).then((isTaken) => {
        console.log(`[MAIN] Initial port check: port 8000 is ${isTaken ? 'TAKEN' : 'FREE'}. isRelaunch: ${isRelaunch}`);
        if (isTaken && !isRelaunch) {
            console.log('[MAIN] Port 8000 is taken. Assuming backend is already running manually.');
            waitForBackend().then(createWindow);
        } else {
            if (isTaken && isRelaunch) {
                console.log('[MAIN] Port 8000 is taken during relaunch. Backend might still be shutting down. Waiting for it to clear...');
                // If it's a relaunch and port is taken, it's likely the old backend still dying.
                // We should wait for it to clear, THEN start a new one.
                waitForPortToClear(8000).then(() => {
                    console.log('[MAIN] Port cleared. Starting fresh Python backend...');
                    startPythonBackend();
                    setTimeout(() => waitForBackend().then(createWindow), 1000);
                });
            } else {
                console.log('[MAIN] Starting Python backend...');
                startPythonBackend();
                // Give it a moment to start, then wait for health check
                setTimeout(() => {
                    waitForBackend().then(createWindow);
                }, 1000);
            }
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

function checkBackendPort(port) {
    return new Promise((resolve) => {
        const net = require('net');
        const server = net.createServer();
        server.once('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(true);
            } else {
                resolve(false);
            }
        });
        server.once('listening', () => {
            server.close();
            resolve(false);
        });
        server.listen(port);
    });
}

function waitForPortToClear(port, retries = 20) {
    return new Promise((resolve) => {
        const check = () => {
            checkBackendPort(port).then((isTaken) => {
                if (!isTaken) {
                    console.log(`[MAIN] Port ${port} is now clear.`);
                    resolve();
                } else if (retries > 0) {
                    console.log(`[MAIN] Port ${port} still taken, waiting... (${retries} retries left)`);
                    setTimeout(() => {
                        retries--;
                        check();
                    }, 500);
                } else {
                    console.log(`[MAIN] Port ${port} didn't clear in time after 10 seconds. Proceeding anyway but it might fail.`);
                    resolve();
                }
            });
        };
        check();
    });
}

function waitForBackend() {
    return new Promise((resolve) => {
        const check = () => {
            const http = require('http');
            http.get('http://127.0.0.1:8000/status', (res) => {
                if (res.statusCode === 200) {
                    console.log('Backend is ready!');
                    resolve();
                } else {
                    console.log('Backend not ready, retrying...');
                    setTimeout(check, 1000);
                }
            }).on('error', (err) => {
                console.log('Waiting for backend...');
                setTimeout(check, 1000);
            });
        };
        check();
    });
}

let windowWasShown = false;

app.on('window-all-closed', () => {
    // Only quit if the window was actually shown at least once
    // This prevents quitting during startup if window creation fails
    if (process.platform !== 'darwin' && windowWasShown) {
        app.quit();
    } else if (!windowWasShown) {
        console.log('Window was never shown - keeping app alive to allow retries');
    }
});

app.on('will-quit', () => {
    console.log('[MAIN] App closing... Killing Python backend.');
    if (pythonProcess) {
        const pid = pythonProcess.pid;
        if (process.platform === 'win32') {
            // Windows: Force kill the process tree synchronously
            try {
                const { execSync } = require('child_process');
                console.log(`[MAIN] Executing taskkill for PID ${pid}...`);
                execSync(`taskkill /pid ${pid} /f /t`);
                console.log(`[MAIN] taskkill for PID ${pid} completed.`);
            } catch (e) {
                console.error(`[MAIN] Failed to kill python process ${pid}: ${e.message}`);
            }
        } else {
            // Unix: SIGKILL
            console.log(`[MAIN] Sending SIGKILL to PID ${pid}...`);
            pythonProcess.kill('SIGKILL');
        }
        pythonProcess = null;
    } else {
        console.log('[MAIN] No pythonProcess found to kill.');
    }
});
