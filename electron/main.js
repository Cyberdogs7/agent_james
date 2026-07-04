const { app, BrowserWindow, ipcMain, Menu, MenuItem } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Function to read port from .env manually
function getServerPort() {
    try {
        const envPath = path.join(__dirname, '../.env');
        if (fs.existsSync(envPath)) {
            const content = fs.readFileSync(envPath, 'utf8');
            const match = content.match(/^SERVER_PORT=(.*)$/m);
            if (match && match[1]) {
                const port = parseInt(match[1].trim(), 10);
                if (!isNaN(port)) return port;
            }
        }
    } catch (e) {
        console.error('Failed to read .env file:', e);
    }
    return 8180; // Default port
}

const SERVER_PORT = getServerPort();
console.log(`[Electron] Using backend port: ${SERVER_PORT}`);

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
            spellcheck: true,
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

    mainWindow.webContents.on('context-menu', (event, params) => {
        const menu = new Menu();

        // Add spelling suggestions if misspelled word exists
        if (params.misspelledWord) {
            for (const suggestion of params.dictionarySuggestions) {
                menu.append(new MenuItem({
                    label: suggestion,
                    click: () => mainWindow.webContents.replaceMisspelling(suggestion)
                }));
            }

            // Only add separator if we had suggestions
            if (params.dictionarySuggestions.length > 0) {
                menu.append(new MenuItem({ type: 'separator' }));
            }

            // Add "Add to dictionary" option
            menu.append(new MenuItem({
                label: 'Add to dictionary',
                click: () => mainWindow.webContents.session.addWordToSpellCheckerDictionary(params.misspelledWord)
            }));
            menu.append(new MenuItem({ type: 'separator' }));
        }

        // Add standard editing options if right-clicked on an editable field or text is selected
        if (params.isEditable || params.selectionText.trim().length > 0) {
            menu.append(new MenuItem({ role: 'cut' }));
            menu.append(new MenuItem({ role: 'copy' }));
            menu.append(new MenuItem({ role: 'paste' }));
            menu.append(new MenuItem({ type: 'separator' }));
            menu.append(new MenuItem({ role: 'selectAll' }));
        }

        // Show menu if there are items in it
        if (menu.items.length > 0) {
            menu.popup();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonBackend() {
    let pythonExecutable = 'python';
    const winVenvPath = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
    const unixVenvPath = path.join(__dirname, '..', '.venv', 'bin', 'python');
    
    if (fs.existsSync(winVenvPath)) {
        pythonExecutable = winVenvPath;
    } else if (fs.existsSync(unixVenvPath)) {
        pythonExecutable = unixVenvPath;
    }

    console.log(`Starting Python backend: ${pythonExecutable} -m backend.server`);

    pythonProcess = spawn(pythonExecutable, ['-m', 'backend.server'], {
        cwd: path.join(__dirname, '..'),
    });

    pythonProcess.on('error', (err) => {
        console.error(`[Python Spawn Error]: Failed to start Python backend. Error:`, err);
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error]: ${data}`);
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

    ipcMain.on('restart_app', () => {
        console.log('[RESTART] Received restart request from renderer process.');
        if (pythonProcess) {
            console.log('[RESTART] Killing existing Python backend...');
            if (process.platform === 'win32') {
                try {
                    const { execSync } = require('child_process');
                    execSync(`taskkill /pid ${pythonProcess.pid} /f /t`);
                } catch (e) {
                    console.error('Failed to kill python process during restart:', e.message);
                }
            } else {
                pythonProcess.kill('SIGKILL');
            }
            pythonProcess = null;
        }

        console.log('[RESTART] Starting new Python backend...');
        startPythonBackend();

        console.log('[RESTART] Waiting for backend to become available...');
        waitForBackend().then(() => {
            console.log('[RESTART] Backend is ready. Reloading window.');
            if (mainWindow) {
                mainWindow.webContents.reload();
            }
        });
    });

    checkBackendPort(SERVER_PORT).then((isTaken) => {
        if (isTaken) {
            console.log(`Port ${SERVER_PORT} is taken. Assuming backend is already running manually.`);
            waitForBackend().then(createWindow);
        } else {
            startPythonBackend();
            // Give it a moment to start, then wait for health check
            setTimeout(() => {
                waitForBackend().then(createWindow);
            }, 1000);
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

function waitForBackend() {
    return new Promise((resolve) => {
        const check = () => {
            const http = require('http');
            http.get(`http://127.0.0.1:${SERVER_PORT}/status`, (res) => {
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
    console.log('App closing... Killing Python backend.');
    if (pythonProcess) {
        if (process.platform === 'win32') {
            // Windows: Force kill the process tree synchronously
            try {
                const { execSync } = require('child_process');
                execSync(`taskkill /pid ${pythonProcess.pid} /f /t`);
            } catch (e) {
                console.error('Failed to kill python process:', e.message);
            }
        } else {
            // Unix: SIGKILL
            pythonProcess.kill('SIGKILL');
        }
        pythonProcess = null;
    }
});
