import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const TOOLS = [
    { id: 'generate_cad', label: 'Generate CAD' },
    { id: 'run_web_agent', label: 'Web Agent' },
    { id: 'create_directory', label: 'Create Folder' },
    { id: 'write_file', label: 'Write File' },
    { id: 'read_directory', label: 'Read Directory' },
    { id: 'read_file', label: 'Read File' },
    { id: 'create_project', label: 'Create Project' },
    { id: 'switch_project', label: 'Switch Project' },
    { id: 'list_projects', label: 'List Projects' },
    { id: 'list_smart_devices', label: 'List Devices' },
    { id: 'control_light', label: 'Control Light' },
    { id: 'discover_printers', label: 'Discover Printers' },
    { id: 'print_stl', label: 'Print 3D Model' },
    { id: 'iterate_cad', label: 'Iterate CAD' },
];

const FREE_MODELS = [
    { id: 'opencode/big-pickle', label: 'Big Pickle (Free)' },
    { id: 'opencode/deepseek-v4-flash-free', label: 'DeepSeek V4 Flash (Free)' },
    { id: 'opencode/minimax-m2.5-free', label: 'MiniMax M2.5 (Free)' },
    { id: 'opencode/nemotron-3-super-free', label: 'Nemotron 3 Super (Free)' },
];

const SettingsWindow = ({
    socket,
    micDevices,
    speakerDevices,
    webcamDevices,
    selectedMicId,
    setSelectedMicId,
    selectedSpeakerId,
    setSelectedSpeakerId,
    selectedWebcamId,
    setSelectedWebcamId,
    cursorSensitivity,
    setCursorSensitivity,
    isCameraFlipped,
    setIsCameraFlipped,
    handleFileUpload,
    onClose
}) => {
    const [permissions, setPermissions] = useState({});
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(false);
    const [apiKeys, setApiKeys] = useState({});
    const [showKey, setShowKey] = useState({});
    const [opencodeSettings, setOpencodeSettings] = useState({
        server_url: 'http://127.0.0.1:4096',
        server_port: 4096,
        auto_start: true,
        use_worktrees: true,
        use_interceptor: true,
        model_tiers: {
            high: 'opencode/big-pickle',
            medium: 'opencode/deepseek-v4-flash-free',
            low: 'opencode/nemotron-3-super-free'
        }
    });

    const updateOpencodeSetting = (key, value) => {
        setOpencodeSettings(prev => ({ ...prev, [key]: value }));
    };

    const updateModelTier = (tier, modelId) => {
        setOpencodeSettings(prev => ({
            ...prev,
            model_tiers: { ...prev.model_tiers, [tier]: modelId }
        }));
    };

    useEffect(() => {
        // Request initial permissions and keys
        socket.emit('get_settings');
        socket.emit('get_api_keys');

        // Listen for updates
        const handleSettings = (settings) => {
            console.log("Received settings:", settings);
            if (settings) {
                if (settings.tool_permissions) setPermissions(settings.tool_permissions);
                if (typeof settings.face_auth_enabled !== 'undefined') {
                    setFaceAuthEnabled(settings.face_auth_enabled);
                    localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
                }
                // Load OpenCode settings
                if (settings.opencode_server_url) {
                    setOpencodeSettings({
                        server_url: settings.opencode_server_url || 'http://127.0.0.1:4096',
                        server_port: settings.opencode_server_port || 4096,
                        auto_start: settings.opencode_auto_start !== false,
                        use_worktrees: settings.opencode_use_worktrees !== false,
                        use_interceptor: settings.opencode_use_interceptor !== false,
                        model_tiers: settings.opencode_model_tiers || {
                            high: 'opencode/big-pickle',
                            medium: 'opencode/deepseek-v4-flash-free',
                            low: 'opencode/nemotron-3-super-free'
                        }
                    });
                }
            }
        };

        const handleApiKeys = (keys) => {
            if (keys) setApiKeys(keys);
        };

        socket.on('settings', handleSettings);
        socket.on('api_keys', handleApiKeys);

        return () => {
            socket.off('settings', handleSettings);
            socket.off('api_keys', handleApiKeys);
        };
    }, [socket]);

    const togglePermission = (toolId) => {
        const currentVal = permissions[toolId] !== false; // Default True
        const nextVal = !currentVal;

        // Update local mostly for responsiveness, but socket roundtrip handles truth
        // setPermissions(prev => ({ ...prev, [toolId]: nextVal }));

        // Send update
        socket.emit('update_settings', { tool_permissions: { [toolId]: nextVal } });
    };

    const toggleFaceAuth = () => {
        const newVal = !faceAuthEnabled;
        setFaceAuthEnabled(newVal); // Optimistic Update
        localStorage.setItem('face_auth_enabled', newVal);
        socket.emit('update_settings', { face_auth_enabled: newVal });
    };

    const toggleCameraFlip = () => {
        const newVal = !isCameraFlipped;
        setIsCameraFlipped(newVal);
        socket.emit('update_settings', { camera_flipped: newVal });
    };

    return (
        <div className="absolute top-20 right-10 bg-black/90 border border-gold9/50 p-4 rounded-lg z-50 w-80  shadow-[0_0_30px_rgba(255,215,0,0.2)]">
            <div className="flex justify-between items-center mb-4 border-b border-gold9/50 pb-2">
                <h2 className="text-gold9 font-bold text-sm uppercase tracking-wider">Settings</h2>
                <button onClick={onClose} className="text-gold8 hover:text-gold9">
                    <X size={16} />
                </button>
            </div>

            {/* Authentication Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Security</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                    <span className="text-gold9/80">Face Authentication</span>
                    <button
                        onClick={toggleFaceAuth}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${faceAuthEnabled ? 'bg-gold9/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${faceAuthEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* Microphone Section */}
            <div className="mb-4">
                <h3 className="text-gold9 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Microphone</h3>
                <select
                    value={selectedMicId}
                    onChange={(e) => setSelectedMicId(e.target.value)}
                    className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none"
                >
                    {micDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Microphone ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Speaker Section */}
            <div className="mb-4">
                <h3 className="text-gold9 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Speaker</h3>
                <select
                    value={selectedSpeakerId}
                    onChange={(e) => setSelectedSpeakerId(e.target.value)}
                    className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none"
                >
                    {speakerDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Speaker ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Webcam Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Webcam</h3>
                <select
                    value={selectedWebcamId}
                    onChange={(e) => setSelectedWebcamId(e.target.value)}
                    className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none"
                >
                    {webcamDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Camera ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Cursor Section */}
            <div className="mb-6">
                <div className="flex justify-between mb-2">
                    <h3 className="text-gold9 font-bold text-xs uppercase tracking-wider opacity-80">Cursor Sensitivity</h3>
                    <span className="text-xs text-gold9">{cursorSensitivity}x</span>
                </div>
                <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={cursorSensitivity}
                    onChange={(e) => setCursorSensitivity(parseFloat(e.target.value))}
                    className="w-full accent-gold9 cursor-pointer h-1 bg-gray-800 rounded-lg appearance-none"
                />
            </div>

            {/* Gesture Control Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Gesture Control</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                    <span className="text-gold9/80">Flip Camera Horizontal</span>
                    <button
                        onClick={toggleCameraFlip}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isCameraFlipped ? 'bg-gold9/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isCameraFlipped ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* API Configuration Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">API Configuration</h3>
                <div className="space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                    {[
                        'GEMINI_API_KEY', 
                        'OPENROUTER_API_KEY', 
                        'OPENROUTER_MODEL', 
                        'LM_STUDIO_BASE_URL', 
                        'LM_STUDIO_MODEL', 
                        'JULES_API_KEY',
                        ...Object.keys(apiKeys || {}).filter(k => k.startsWith('JULES_API_KEY_')),
                        'TRELLO_API_KEY', 
                        'GIPHY_API_KEY'
                    ].map(keyName => (
                        <div key={keyName} className="flex flex-col gap-1">
                            <label className="text-[10px] text-gold8/60 uppercase">{keyName.replace(/_/g, ' ')}</label>
                            <div className="flex gap-2">
                                <input
                                    type={showKey[keyName] ? "text" : "password"}
                                    value={apiKeys[keyName] || ''}
                                    onChange={(e) => setApiKeys(prev => ({ ...prev, [keyName]: e.target.value }))}
                                    className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none font-mono"
                                />
                                <button
                                    onClick={() => setShowKey(prev => ({ ...prev, [keyName]: !prev[keyName] }))}
                                    className="text-gold8 hover:text-gold9 px-2 bg-gray-900 border border-gold8 rounded text-[10px] uppercase tracking-wider"
                                >
                                    {showKey[keyName] ? 'Hide' : 'Show'}
                                </button>
                                <button
                                    onClick={() => {
                                        socket.emit('delete_api_key', keyName);
                                        setApiKeys(prev => {
                                            const newKeys = { ...prev };
                                            delete newKeys[keyName];
                                            return newKeys;
                                        });
                                    }}
                                    className="text-red-500 hover:text-red-400 px-2 bg-gray-900 border border-red-500/50 rounded text-[10px] uppercase tracking-wider"
                                    title="Delete Key"
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                    <button
                        onClick={() => socket.emit('update_api_keys', apiKeys)}
                        className="w-full mt-2 py-2 bg-gold9/20 hover:bg-gold9/30 text-gold9 border border-gold9/50 rounded text-xs uppercase tracking-wider font-bold transition-colors"
                    >
                        Save API Keys
                    </button>
                </div>
            </div>

            {/* Tool Permissions Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Tool Confirmations</h3>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                    {TOOLS.map(tool => {
                        const isRequired = permissions[tool.id] !== false; // Default True
                        return (
                            <div key={tool.id} className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                                <span className="text-gold9/80">{tool.label}</span>
                                <button
                                    onClick={() => togglePermission(tool.id)}
                                    className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isRequired ? 'bg-gold9/80' : 'bg-gray-700'}`}
                                >
                                    <div
                                        className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isRequired ? 'translate-x-4' : 'translate-x-0'}`}
                                    />
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* OpenCode Section */}
            <div className="mb-6">
                <h3 className="text-gold9 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">OpenCode Configuration</h3>
                <div className="space-y-3">
                    {/* Server URL */}
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-gold8/60 uppercase">Server URL</label>
                        <input
                            type="text"
                            value={opencodeSettings.server_url || 'http://127.0.0.1:4096'}
                            onChange={(e) => updateOpencodeSetting('server_url', e.target.value)}
                            className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none font-mono"
                        />
                    </div>

                    {/* Port */}
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-gold8/60 uppercase">Server Port</label>
                        <input
                            type="number"
                            value={opencodeSettings.server_port || 4096}
                            onChange={(e) => updateOpencodeSetting('server_port', parseInt(e.target.value) || 4096)}
                            className="w-full bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none font-mono"
                        />
                    </div>

                    {/* Toggles */}
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                        <span className="text-gold9/80">Auto-start Server</span>
                        <button
                            onClick={() => updateOpencodeSetting('auto_start', !opencodeSettings.auto_start)}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${opencodeSettings.auto_start ? 'bg-gold9/80' : 'bg-gray-700'}`}
                        >
                            <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${opencodeSettings.auto_start ? 'translate-x-4' : 'translate-x-0'}`} />
                        </button>
                    </div>

                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                        <span className="text-gold9/80">Use Workspaces (Git Worktrees)</span>
                        <button
                            onClick={() => updateOpencodeSetting('use_worktrees', !opencodeSettings.use_worktrees)}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${opencodeSettings.use_worktrees ? 'bg-gold9/80' : 'bg-gray-700'}`}
                        >
                            <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${opencodeSettings.use_worktrees ? 'translate-x-4' : 'translate-x-0'}`} />
                        </button>
                    </div>

                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-gold9/30">
                        <span className="text-gold9/80">Use Triage Interceptor</span>
                        <button
                            onClick={() => updateOpencodeSetting('use_interceptor', !opencodeSettings.use_interceptor)}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${opencodeSettings.use_interceptor ? 'bg-gold9/80' : 'bg-gray-700'}`}
                        >
                            <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${opencodeSettings.use_interceptor ? 'translate-x-4' : 'translate-x-0'}`} />
                        </button>
                    </div>

                    {/* Model Tiers */}
                    <div className="mt-3">
                        <label className="text-[10px] text-gold8/60 uppercase block mb-2">Model Tiers (Free Models)</label>
                        {['high', 'medium', 'low'].map(tier => (
                            <div key={tier} className="flex items-center gap-2 mb-2">
                                <span className="text-[10px] text-gold9/60 uppercase w-12">{tier}</span>
                                <select
                                    value={opencodeSettings.model_tiers?.[tier] || ''}
                                    onChange={(e) => updateModelTier(tier, e.target.value)}
                                    className="flex-1 bg-gray-900 border border-gold8 rounded p-2 text-xs text-gold9 focus:border-gold9 outline-none"
                                >
                                    {FREE_MODELS.map(m => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                        ))}
                    </div>

                    {/* Save Button */}
                    <button
                        onClick={() => socket.emit('update_settings', {
                            opencode_server_url: opencodeSettings.server_url,
                            opencode_server_port: opencodeSettings.server_port,
                            opencode_auto_start: opencodeSettings.auto_start,
                            opencode_use_worktrees: opencodeSettings.use_worktrees,
                            opencode_use_interceptor: opencodeSettings.use_interceptor,
                            opencode_model_tiers: opencodeSettings.model_tiers
                        })}
                        className="w-full mt-2 py-2 bg-gold9/20 hover:bg-gold9/30 text-gold9 border border-gold9/50 rounded text-xs uppercase tracking-wider font-bold transition-colors"
                    >
                        Save OpenCode Settings
                    </button>
                </div>
            </div>

            {/* Memory Section */}
            <div>
                <h3 className="text-gold9 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Memory Data</h3>
                <div className="flex flex-col gap-2">
                    <label className="text-[10px] text-gold8/60 uppercase">Upload Memory Text</label>
                    <input
                        type="file"
                        accept=".txt"
                        onChange={handleFileUpload}
                        className="text-xs text-gold9 bg-gray-900 border border-gold8 rounded p-2 file:mr-2 file:py-1 file:px-2 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-gold9 file:text-gold9 hover:file:bg-gold8 cursor-pointer"
                    />
                </div>
            </div>
        </div>
    );
};

export default React.memo(SettingsWindow);
