import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity,
    Wifi,
    Cpu,
    Layers,
    CheckSquare,
    Printer,
    Zap,
    Clock,
    Globe,
    Shield,
    AlertCircle,
    Plus,
    Trash2,
    Play,
    Terminal
} from 'lucide-react';

const WarRoomDashboard = ({ data, socket, onClose }) => {
    const [time, setTime] = useState(new Date());
    const [showCommandModal, setShowCommandModal] = useState(false);
    const [activeTab, setActiveTab] = useState('tasks'); // 'trello' or 'tasks'

    // Stream control
    useEffect(() => {
        if (socket) {
            socket.emit('start_dashboard_stream');
        }
        return () => {
            if (socket) {
                socket.emit('stop_dashboard_stream');
            }
        };
    }, [socket]);

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Destructure data with defaults
    const {
        project = "UNKNOWN",
        trello = [],
        tasks = [],
        jules = [],
        devices = [],
        printers = [],
        git = { branch: 'unknown', branches: [], status: '' },
        system_status = "ONLINE",
        system_stats = { cpu: 0, ram: 0, net_sent: 0, net_recv: 0 }
    } = data || {};

    const containerVariants = {
        hidden: { opacity: 0, scale: 0.95 },
        visible: {
            opacity: 1,
            scale: 1,
            transition: { duration: 0.5, staggerChildren: 0.1 }
        },
        exit: { opacity: 0, scale: 0.95 }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    const handleDeleteTask = (id) => {
        if (socket) socket.emit('delete_task', { id });
    };

    const handleRunTask = (id) => {
        if (socket) socket.emit('run_task', { id });
    };

    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex flex-col p-6 text-gold9 font-mono overflow-hidden"
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={containerVariants}
            >
                {/* BACKGROUND HUD ELEMENTS */}
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-0 left-0 w-64 h-64 border-l-2 border-t-2 border-gold9/30 rounded-tl-3xl"></div>
                    <div className="absolute top-0 right-0 w-64 h-64 border-r-2 border-t-2 border-gold9/30 rounded-tr-3xl"></div>
                    <div className="absolute bottom-0 left-0 w-64 h-64 border-l-2 border-b-2 border-gold9/30 rounded-bl-3xl"></div>
                    <div className="absolute bottom-0 right-0 w-64 h-64 border-r-2 border-b-2 border-gold9/30 rounded-br-3xl"></div>
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-gold9/5 rounded-full"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-dashed border-gold9/10 rounded-full animate-spin-slow"></div>
                </div>

                {/* HEADER */}
                <motion.header variants={itemVariants} className="relative z-10 flex justify-between items-center mb-6 border-b border-gold9/20 pb-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gold9/10 border border-gold9 rounded-lg flex items-center justify-center">
                            <Shield className="w-6 h-6 text-gold9" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold tracking-[0.2em] text-gold9 drop-shadow-[0_0_10px_rgba(255,215,0,0.5)]">
                                WAR ROOM
                            </h1>
                            <div className="flex items-center gap-2 text-xs text-gold9/60 tracking-widest">
                                <span>OPERATION: {project.toUpperCase()}</span>
                                <span className="w-1 h-1 bg-gold9 rounded-full"></span>
                                <span className={system_status === "ONLINE" ? "text-green-500" : "text-red-500"}>
                                    SYSTEM {system_status}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        <button
                            onClick={() => setShowCommandModal(true)}
                            className="px-4 py-2 bg-gold9/10 border border-gold9 hover:bg-gold9 hover:text-black rounded text-xs tracking-widest transition-all flex items-center gap-2"
                        >
                            <Terminal size={14} />
                            COMMAND
                        </button>
                        <div className="text-right hidden md:block">
                            <div className="text-2xl font-bold tracking-widest">
                                {time.toLocaleTimeString([], { hour12: false })}
                            </div>
                            <div className="text-xs text-gold9/60 tracking-[0.2em]">
                                {time.toLocaleDateString().toUpperCase()}
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 border border-gold9/30 hover:bg-gold9/10 hover:border-gold9 rounded text-xs tracking-widest transition-all"
                        >
                            CLOSE HUD
                        </button>
                    </div>
                </motion.header>

                {/* MAIN GRID */}
                <div className="relative z-10 grid grid-cols-12 grid-rows-6 gap-6 flex-1 min-h-0">

                    {/* COL 1: INTEL (TASKS / TRELLO) - Spans 4 cols, full height */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-4 row-span-6 bg-black/40 border border-gold9/20 rounded-xl p-4 flex flex-col relative overflow-hidden group hover:border-gold9/40 transition-colors"
                    >
                        <div className="absolute top-0 right-0 p-2 opacity-50">
                            <Layers className="w-24 h-24 text-gold9/5" />
                        </div>

                        {/* Tabs */}
                        <div className="flex items-center gap-4 border-b border-gold9/10 pb-2 mb-4">
                            <button
                                onClick={() => setActiveTab('tasks')}
                                className={`text-sm font-bold tracking-widest transition-colors ${activeTab === 'tasks' ? 'text-gold9' : 'text-gold9/40 hover:text-gold9/70'}`}
                            >
                                AUTOMATIONS
                            </button>
                            <button
                                onClick={() => setActiveTab('trello')}
                                className={`text-sm font-bold tracking-widest transition-colors ${activeTab === 'trello' ? 'text-gold9' : 'text-gold9/40 hover:text-gold9/70'}`}
                            >
                                OBJECTIVES
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto scrollbar-hide space-y-3">
                            {activeTab === 'tasks' ? (
                                tasks.length === 0 ? (
                                    <div className="text-center text-gold9/40 py-10 italic text-xs">
                                        No active worker nodes.
                                        <br/>Click COMMAND to deploy.
                                    </div>
                                ) : (
                                    tasks.map((task, i) => (
                                        <div key={i} className="bg-gold9/5 border border-gold9/10 p-3 rounded hover:bg-gold9/10 transition-colors group/item">
                                            <div className="flex justify-between items-start mb-1">
                                                <div className="text-sm font-bold text-gold9">{task.title}</div>
                                                <div className="flex items-center gap-2">
                                                    {task.trigger.type === 'manual' && (
                                                        <button
                                                            onClick={() => handleRunTask(task.id)}
                                                            className="text-green-400 hover:text-green-300 p-1 rounded hover:bg-green-500/20 transition-colors"
                                                            title="Run Now"
                                                        >
                                                            <Play size={12} fill="currentColor" />
                                                        </button>
                                                    )}
                                                    <button onClick={() => handleDeleteTask(task.id)} className="text-gold9/20 hover:text-red-500 transition-colors">
                                                        <Trash2 size={12} />
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="text-[10px] text-gold9/50 flex gap-2">
                                                <span className="bg-gold9/10 px-1 rounded">TRIG: {task.trigger.type.toUpperCase()}</span>
                                                <span className="bg-blue-500/10 text-blue-400 px-1 rounded">ACT: {task.action.type.toUpperCase()}</span>
                                            </div>
                                        </div>
                                    ))
                                )
                            ) : (
                                trello.length === 0 ? (
                                    <div className="text-center text-gold9/40 py-10 italic">No active objectives detected.</div>
                                ) : (
                                    trello.map((card, i) => (
                                        <div key={i} className="bg-gold9/5 border border-gold9/10 p-3 rounded hover:bg-gold9/10 transition-colors">
                                            <div className="text-xs text-gold9/50 mb-1 flex justify-between">
                                                <span>{card.listName || 'PENDING'}</span>
                                                <span>#{card.idShort}</span>
                                            </div>
                                            <div className="font-medium text-sm text-gray-200">{card.name}</div>
                                        </div>
                                    ))
                                )
                            )}
                        </div>
                    </motion.div>

                    {/* COL 2: CENTER COMMS (JULES) - Spans 5 cols, Top 4 rows */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-5 row-span-4 bg-black/40 border border-gold9/20 rounded-xl p-4 flex flex-col relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-2 opacity-50">
                            <Activity className="w-24 h-24 text-gold9/5" />
                        </div>
                        <h2 className="flex items-center gap-2 text-lg font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                            <Cpu className="w-5 h-5 text-gold9" />
                            AGENT STATUS (JULES)
                        </h2>
                        <div className="flex-1 overflow-y-auto scrollbar-hide">
                             {jules.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-gold9/40 gap-2">
                                    <Activity className="w-8 h-8 opacity-50" />
                                    <span className="italic">No active agents in field.</span>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-3">
                                    {jules.map((session, i) => (
                                        <div key={i} className="flex items-center gap-3 bg-gold9/5 border border-gold9/10 p-3 rounded cursor-pointer hover:bg-gold9/20 transition-colors">
                                            <div className={`w-2 h-2 rounded-full ${session.state === 'RUNNING' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                                            <div className="flex-1">
                                                <div className="text-sm font-bold text-gold9">{session.title || session.id}</div>
                                                <div className="text-xs text-gold9/60">STATE: {session.state || 'UNKNOWN'}</div>
                                            </div>
                                            <div className="text-xs font-mono text-gold9/40">
                                                ID: {session.id.substring(0,6)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>

                    {/* COL 2 BOTTOM: QUICK STATS - Spans 5 cols, Bottom 2 rows */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-5 row-span-2 grid grid-cols-3 gap-4"
                    >
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">RAM LOAD</div>
                            <div className="text-2xl font-bold text-green-400">{system_stats.ram.toFixed(1)}%</div>
                            <Activity className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">CPU LOAD</div>
                            <div className="text-2xl font-bold text-gold9">{system_stats.cpu.toFixed(1)}%</div>
                            <Cpu className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                            <div className="text-xs text-gold9/60">NETWORK</div>
                            <div className="text-[10px] font-bold text-blue-400 font-mono">
                                <div>TX: {(system_stats.net_sent / 1024 / 1024).toFixed(1)} MB</div>
                                <div>RX: {(system_stats.net_recv / 1024 / 1024).toFixed(1)} MB</div>
                            </div>
                            <Globe className="w-4 h-4 self-end text-gold9/30" />
                        </div>
                    </motion.div>

                    {/* COL 3: HARDWARE (DEVICES/PRINTERS/GIT) - Spans 3 cols, full height */}
                    <motion.div
                        variants={itemVariants}
                        className="col-span-3 row-span-6 flex flex-col gap-4"
                    >
                        {/* GIT OPS */}
                        <div className="bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                             <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-2">
                                <span className="text-gold9">GIT OPS</span>
                            </h2>
                            <div className="text-xs space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-gold9/60">BRANCH</span>
                                    <span className="font-bold text-green-400">{git.branch}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gold9/60">STATUS</span>
                                    <span className="font-mono text-[10px]">{git.status ? 'MODIFIED' : 'CLEAN'}</span>
                                </div>
                            </div>
                        </div>

                        {/* PRINTERS */}
                        <div className="flex-1 bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                             <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                                <Printer className="w-4 h-4 text-gold9" />
                                FABRICATION
                            </h2>
                            <div className="space-y-3">
                                {printers.length === 0 ? (
                                    <div className="text-xs text-gold9/40 italic">No units online.</div>
                                ) : (
                                    printers.map((p, i) => (
                                        <div key={i} className="bg-gold9/5 p-2 rounded border border-gold9/10">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="text-xs font-bold">{p.name}</span>
                                                <div className={`w-1.5 h-1.5 rounded-full ${p.state === 'printing' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                                            </div>
                                            <div className="text-[10px] text-gold9/60 flex justify-between">
                                                <span>{p.state || 'IDLE'}</span>
                                                <span>{p.temp ? `${p.temp}°C` : '--'}</span>
                                            </div>
                                            {p.progress > 0 && (
                                                <div className="w-full h-1 bg-gray-800 rounded-full mt-2 overflow-hidden">
                                                    <div className="h-full bg-gold9" style={{ width: `${p.progress}%` }}></div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* DEVICES */}
                        <div className="flex-1 bg-black/40 border border-gold9/20 rounded-xl p-4 relative overflow-hidden">
                            <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest border-b border-gold9/10 pb-2 mb-4">
                                <Zap className="w-4 h-4 text-gold9" />
                                FIELD ASSETS
                            </h2>
                            <div className="space-y-2 max-h-[200px] overflow-y-auto scrollbar-hide">
                                 {devices.length === 0 ? (
                                    <div className="text-xs text-gold9/40 italic">No assets detected.</div>
                                ) : (
                                    devices.map((d, i) => (
                                        <div key={i} className="flex items-center justify-between bg-gold9/5 p-2 rounded border border-gold9/10">
                                            <span className="text-xs truncate max-w-[100px]">{d.alias}</span>
                                            <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${d.is_on ? 'bg-gold9 text-black' : 'bg-gray-800 text-gray-500'}`}>
                                                {d.is_on ? 'ON' : 'OFF'}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </motion.div>

                </div>

                {/* FOOTER */}
                <motion.div variants={itemVariants} className="mt-4 text-[10px] text-gold9/40 flex justify-between uppercase tracking-widest">
                    <div>SECURE CONNECTION ESTABLISHED</div>
                    <div>A.D.A OS v2.0 // AUTH: JAMES</div>
                </motion.div>

                {/* COMMAND MODAL */}
                {showCommandModal && (
                    <CommandModal
                        onClose={() => setShowCommandModal(false)}
                        socket={socket}
                    />
                )}

            </motion.div>
        </AnimatePresence>
    );
};

const CommandModal = ({ onClose, socket }) => {
    const [title, setTitle] = useState('');
    const [triggerType, setTriggerType] = useState('manual');
    const [triggerValue, setTriggerValue] = useState('');
    const [actionType, setActionType] = useState('jules_task');
    const [actionValue, setActionValue] = useState('');
    const [selectedSource, setSelectedSource] = useState('');
    const [availableSources, setAvailableSources] = useState([]);

    // Fetch sources on mount
    useEffect(() => {
        if (socket) {
            socket.emit('get_jules_sources');

            const handleSources = (sources) => {
                // sources can be a list of strings or objects. normalize.
                // handle_list_jules_sources usually returns dicts like {name: '...', displayName: '...'}
                const normalized = sources.map(s => typeof s === 'string' ? s : (s.name || s.id));
                setAvailableSources(normalized);
                if (normalized.length > 0) setSelectedSource(normalized[0]);
            };

            socket.on('jules_sources', handleSources);
            return () => socket.off('jules_sources', handleSources);
        }
    }, [socket]);

    const handleSubmit = (e) => {
        e.preventDefault();

        let finalActionValue = actionValue;
        if (actionType === 'jules_task') {
            finalActionValue = {
                prompt: actionValue,
                source: selectedSource
            };
        }

        if (socket) {
            socket.emit('create_task', {
                title,
                trigger_type: triggerType,
                trigger_value: triggerValue,
                action_type: actionType,
                action_value: finalActionValue
            });
        }
        onClose();
    };

    return (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-black border border-gold9 p-6 rounded-xl w-[400px] relative shadow-[0_0_50px_rgba(255,215,0,0.2)]">
                <button onClick={onClose} className="absolute top-2 right-2 text-gold9/50 hover:text-gold9">
                    ✕
                </button>
                <h2 className="text-xl font-bold text-gold9 mb-4 flex items-center gap-2">
                    <Terminal size={18} />
                    NEW AUTOMATION
                </h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs text-gold9/60 mb-1">TASK TITLE</label>
                        <input
                            type="text"
                            required
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
                            placeholder="e.g. Bug Fix Routine"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-gold9/60 mb-1">TRIGGER</label>
                            <select
                                value={triggerType}
                                onChange={(e) => setTriggerType(e.target.value)}
                                className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 outline-none"
                            >
                                <option value="manual">MANUAL</option>
                                <option value="schedule">SCHEDULE</option>
                                <option value="git">GIT EVENT</option>
                                <option value="trello">TRELLO CARD</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-gold9/60 mb-1">ACTION</label>
                            <select
                                value={actionType}
                                onChange={(e) => setActionType(e.target.value)}
                                className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 outline-none"
                            >
                                <option value="jules_task">JULES TASK</option>
                                <option value="notify">NOTIFY</option>
                                <option value="run_script">RUN SCRIPT</option>
                            </select>
                        </div>
                    </div>

                    {(triggerType === 'schedule' || triggerType === 'git' || triggerType === 'trello') && (
                        <div>
                            <label className="block text-xs text-gold9/60 mb-1">
                                {triggerType === 'schedule' ? 'CRON / TIME' : 'EVENT DETAIL'}
                            </label>
                            <input
                                type="text"
                                value={triggerValue}
                                onChange={(e) => setTriggerValue(e.target.value)}
                                className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
                                placeholder={triggerType === 'schedule' ? '0 12 * * *' : 'Trigger Value'}
                            />
                        </div>
                    )}

                    {actionType === 'jules_task' && (
                        <>
                            <div>
                                <label className="block text-xs text-gold9/60 mb-1">SOURCE / REPO</label>
                                <select
                                    value={selectedSource}
                                    onChange={(e) => setSelectedSource(e.target.value)}
                                    className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 outline-none"
                                >
                                    <option value="">-- Select Source --</option>
                                    {availableSources.map((s, i) => (
                                        <option key={i} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs text-gold9/60 mb-1">TASK PROMPT</label>
                                <textarea
                                    required
                                    value={actionValue}
                                    onChange={(e) => setActionValue(e.target.value)}
                                    className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none h-20 resize-none"
                                    placeholder="Describe the task for Jules..."
                                />
                            </div>
                        </>
                    )}

                    {(actionType === 'run_script' || actionType === 'notify') && (
                        <div>
                            <label className="block text-xs text-gold9/60 mb-1">
                                {actionType === 'run_script' ? 'SCRIPT PATH' : 'MESSAGE'}
                            </label>
                            <input
                                type="text"
                                value={actionValue}
                                onChange={(e) => setActionValue(e.target.value)}
                                className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
                                placeholder={actionType === 'run_script' ? './scripts/backup.sh' : 'Notification Text'}
                            />
                        </div>
                    )}

                    <button
                        type="submit"
                        className="w-full bg-gold9 text-black font-bold py-2 rounded hover:bg-yellow-400 transition-colors tracking-widest mt-4"
                    >
                        {triggerType === 'manual' ? 'SAVE ROUTINE' : 'INITIALIZE ROUTINE'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default WarRoomDashboard;
