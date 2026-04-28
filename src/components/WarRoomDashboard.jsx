import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Activity,
    Cpu,
    Layers,
    CheckSquare,
    Printer,
    Zap,
    Clock,
    Shield,
    AlertCircle,
    Plus,
    Trash2,
    Play,
    Terminal,
    MessageSquare,
    Send,
    ThumbsUp,
    FileCode,
    GitCommit,
    CheckCircle,
    List,
    X,
    Server,
    GitBranch,
    GitMerge
} from 'lucide-react';
import AutomationEditor from './AutomationEditor';
import FleetManagerUI from './FleetManagerUI';
import ClockDisplay from './ClockDisplay';


const WarRoomDashboard = ({ data, socket, onClose, messages = [], inputValue, setInputValue, handleSend }) => {
    const [showCommandModal, setShowCommandModal] = useState(false);
    const [showEditor, setShowEditor] = useState(false);
        const [selectedSession, setSelectedSession] = useState(null);
    const [selectedArtifact, setSelectedArtifact] = useState(null);
    const [fleetStatus, setFleetStatus] = useState([]);
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [selectedRepo, setSelectedRepo] = useState(null);
    const [swarms, setSwarms] = useState([]);
    const [selectedFleetAgent, setSelectedFleetAgent] = useState(null);
    const [selectedTask, setSelectedTask] = useState(null);
        const [fleetState, setFleetState] = useState({ agents: [], repos: [] });
    const [autoMergeMaster, setAutoMergeMaster] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Add effect for settings fetch
    useEffect(() => {
        if (socket) {
            socket.emit('get_settings');
            const handleSettings = (settings) => {
                if (settings && typeof settings.auto_merge_master !== 'undefined') {
                    setAutoMergeMaster(settings.auto_merge_master);
                }
            };
            socket.on('settings', handleSettings);
            return () => socket.off('settings', handleSettings);
        }
    }, [socket]);

    // Add effect for fleet state
    useEffect(() => {
        if (socket) {
            socket.emit('get_fleet_state');
            const handleFleetState = (data) => setFleetState(data);
            socket.on('fleet_state_update', handleFleetState);
            return () => socket.off('fleet_state_update', handleFleetState);
        }
    }, [socket]);

    useEffect(() => {
        if (selectedRepo) {
            const updatedRepo = fleetStatus.find(r => r.name === selectedRepo.name);
            if (updatedRepo && JSON.stringify(updatedRepo) !== JSON.stringify(selectedRepo)) {
                setSelectedRepo(updatedRepo);
            }
        }
    }, [fleetStatus, selectedRepo]);


    // Stream control
    useEffect(() => {
        if (socket) {
            socket.emit('start_dashboard_stream');
            // Initial fleet status fetch
            socket.emit('get_fleet_status');
            socket.emit('get_swarms');

            const handleFleetStatus = (data) => {
                setFleetStatus(data);
            };
            const handleSwarms = (data) => {
                setSwarms(data);
            };
            const handleError = (err) => {
                if (err.code === 'AUTH_REQUIRED') {
                    setShowAuthModal(true);
                }
            };

            socket.on('fleet_status_update', handleFleetStatus);
            socket.on('swarms_update', handleSwarms);
            socket.on('error', handleError);
            return () => {
                socket.off('fleet_status_update', handleFleetStatus);
                socket.off('swarms_update', handleSwarms);
                socket.off('error', handleError);
                socket.emit('stop_dashboard_stream');
            };
        }
    }, [socket]);

    // Destructure data with defaults
    const {
        project = "UNKNOWN",
        trello = [],
        tasks = [],
        jules = [],
        devices = [],
        printers = [],
        // git = { branch: 'unknown', branches: [], status: '' }, // Deprecated single-repo view
        system_status = "ONLINE",
        system_stats = { total_agents: 0, active_agents: 0, completed_agents: 0, success_rate: 0 }
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

    const handleDeleteObjective = (id) => {
        if (socket) socket.emit('delete_trello_card', { id });
    };

    const handleRunTask = (id) => {
        if (socket) socket.emit('run_task', { id });
    };

    const handleApplyFix = (id) => {
        if (socket) socket.emit('apply_task_fix', { id });
    };

    const handleDismissJules = (id) => {
        if (socket) socket.emit('dismiss_jules_session', { id });
    };

    const openSessionDetails = (session) => {
        setSelectedSession(session);
        if (socket) {
            socket.emit('set_focused_session', { id: session.id });
        }
    };

    const closeSessionDetails = () => {
        setSelectedSession(null);
        if (socket) {
            socket.emit('clear_focused_session');
        }
    };

    const handleRepoDragStart = (e, repoName) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('application/repo', repoName);
    };

    const handleSyncFleet = () => {
        if (socket) {
            socket.emit('sync_fleet');
        }
    };

    const getRoleFromTitle = (title) => {
        const match = title.match(/^\[(.*?)\]\s*(.*)/);
        if (match) {
            return { role: match[1], cleanTitle: match[2] };
        }
        return { role: null, cleanTitle: title };
    };

    const roleColors = {
        'FRONTEND': 'text-blue-400 border-blue-500/50 bg-blue-500/20',
        'BACKEND': 'text-green-400 border-green-500/50 bg-green-500/20',
        'QA': 'text-yellow-400 border-yellow-500/50 bg-yellow-500/20',
        'SECURITY': 'text-red-400 border-red-500/50 bg-red-500/20',
        'DEVOPS': 'text-purple-400 border-purple-500/50 bg-purple-500/20',
        'DEFAULT': 'text-gold9 border-gold9/50 bg-gold9/20'
    };

    // Helper to organize sessions into swarms and solo
    // ⚡ Bolt: Memoized expensive array mapping and filtering to prevent recalculation on every render
    const { swarmGroups, soloSessions } = React.useMemo(() => {
        const swarmGroups = swarms.map(swarm => {
            const swarmSessions = jules.filter(s => swarm.sessions.includes(s.id));
            return {
                ...swarm,
                activeSessions: swarmSessions
            };
        }).filter(g => g.activeSessions.length > 0 || (Date.now() / 1000 - g.created_at < 3600)); // Show active or recent swarms

        const swarmSessionIds = new Set(swarms.flatMap(s => s.sessions));
        const soloSessions = jules.filter(s => !swarmSessionIds.has(s.id));

        return { swarmGroups, soloSessions };
    }, [swarms, jules]);

    const renderSessionItem = (session, i) => {
        const { role, cleanTitle } = getRoleFromTitle(session.title || session.id);
        const roleStyle = role ? (roleColors[role.toUpperCase()] || roleColors['DEFAULT']) : '';

        return (
            <div
                key={session.id}
                onClick={() => openSessionDetails(session)}
                className="flex items-center gap-3 bg-gold9/5 border border-gold9/10 p-3 rounded cursor-pointer hover:bg-gold9/20 transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_15px_rgba(255,215,0,0.1)] group/item mb-2 last:mb-0"
            >
                <div className={`w-2 h-2 rounded-full ${session.state === 'RUNNING' || session.state === 'IN_PROGRESS' ? 'bg-green-500 animate-pulse' : (session.state === 'COMPLETED' ? 'bg-blue-500' : 'bg-gray-500')}`}></div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                        {role && (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider border ${roleStyle}`}>
                                {role.toUpperCase()}
                            </span>
                        )}
                        <div className="text-sm font-bold text-gold9 truncate">{cleanTitle}</div>
                    </div>
                    <div className="text-xs text-gold9/60">STATE: {session.state || 'UNKNOWN'}</div>
                    {session.latest_thought && (
                        <div className="text-xs text-gold9/40 italic truncate mt-1">
                            "{session.latest_thought}"
                        </div>
                    )}
                </div>
                <div className="text-xs font-mono text-gold9/40 mr-2">
                    ID: {session.id.substring(0, 6)}
                </div>
                <button onClick={(e) => { e.stopPropagation(); handleDismissJules(session.id); }} className="text-gold9/20 hover:text-red-500 transition-colors opacity-0 group-hover/item:opacity-100">
                    <Trash2 size={14} />
                </button>
            </div>
        );
    };


    // Calculate stats from fleetState
    const activeAgentsCount = fleetState.agents.filter(a => a.status === 'working').length;
    let totalTasks = 0;
    let completedTasks = 0;
    fleetState.repos.forEach(repo => {
        if (repo.queue) {
            totalTasks += repo.queue.length;
            repo.queue.forEach(task => {
                if (task.status === 'completed') completedTasks++;
            });
        }
    });
    const successRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 z-[100] bg-black/90  flex flex-col p-6 text-gold9 font-mono overflow-hidden"
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={containerVariants}
                style={{ WebkitAppRegion: 'no-drag', pointerEvents: 'auto' }}
            >
                {/* BACKGROUND HUD ELEMENTS */}
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-0 left-0 w-64 h-64 border-l-2 border-t-2 border-gold9/30 rounded-tl-3xl"></div>
                    <div className="absolute top-0 right-0 w-64 h-64 border-r-2 border-t-2 border-gold9/30 rounded-tr-3xl"></div>
                    <div className="absolute bottom-0 left-0 w-64 h-64 border-l-2 border-b-2 border-gold9/30 rounded-bl-3xl"></div>
                    <div className="absolute bottom-0 right-0 w-64 h-64 border-r-2 border-b-2 border-gold9/30 rounded-br-3xl"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-gold9/5 rounded-full"></div>
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-dashed border-gold9/10 rounded-full animate-spin-slow"></div>
                </div>

                {/* HEADER */}
                <motion.header variants={itemVariants} className="relative z-10 flex justify-between items-center mb-6 border-b border-gold9/20 pb-4" style={{ WebkitAppRegion: 'drag' }}>
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
                    <div className="flex items-center gap-6" style={{ WebkitAppRegion: 'no-drag', pointerEvents: 'auto' }}>
                        <button
                            onClick={() => setShowEditor(true)}
                            className="px-4 py-2 bg-gold9/10 border border-gold9 hover:bg-gold9 hover:text-black rounded text-xs tracking-widest transition-all flex items-center gap-2"
                        >
                            <Cpu size={14} />
                            EDITOR
                        </button>
                        <button
                            data-testid="open-command-modal"
                            onClick={() => setShowCommandModal(true)}
                            className="px-4 py-2 bg-gold9/10 border border-gold9 hover:bg-gold9 hover:text-black rounded text-xs tracking-widest transition-all flex items-center gap-2"
                        >
                            <Terminal size={14} />
                            COMMAND
                        </button>
                        <ClockDisplay />
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

                    {/* FLEET MANAGER (AGENT POOL + KINETIC COMMAND) */}
                    <div className="col-span-9 row-span-6 bg-black/80 border border-gold9/20 rounded-xl overflow-hidden flex flex-col">
                        <FleetManagerUI
                            fleetState={fleetState}
                            fleetStatus={fleetStatus}
                            julesSessions={jules}
                            onAssign={(agentId, repoName) => socket.emit('assign_agent_to_repo', { agent_id: agentId, repo_name: repoName })}
                            onUnassign={(agentId) => socket.emit('unassign_agent', { agent_id: agentId })}
                            onAddTask={(repoName, prompt, dependsOn, attachments) => socket.emit('add_task_to_repo_queue', { repo_name: repoName, prompt, depends_on: dependsOn, attachments })}
                            onRemoveTask={(repoName, taskId) => socket.emit('remove_task_from_queue', { repo_name: repoName, task_id: taskId })}
                            onRetryTask={(repoName, taskId) => socket.emit('retry_task', { repo_name: repoName, task_id: taskId })}
                            onClearCompleted={(repoName) => socket.emit('clear_completed_tasks', { repo_name: repoName })}
                            onToggleRepoActive={(repoName, isActive) => socket.emit('set_repo_active_state', { repo_name: repoName, is_active: isActive })}
                            onAgentClick={setSelectedFleetAgent}
                            onTaskClick={(task, repoName) => setSelectedTask({...task, repoName})}
                            autoMergeMaster={autoMergeMaster}
                            onToggleAutoMergeMaster={(val) => {
                                setAutoMergeMaster(val);
                                socket.emit('update_settings', { auto_merge_master: val });
                            }}
                        />
                    </div>

                    {/* RIGHT COLUMN: FLEET COMMAND (GIT) & STATS */}
                    <div className="col-span-3 row-span-6 flex flex-col gap-6">
                        {/* STATS */}
                        <motion.div variants={itemVariants} className="grid grid-cols-2 gap-4">
                            <div className="bg-black/80 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                                <div className="text-xs text-gold9/60">ACTIVE AGENTS</div>
                                <div className="text-2xl font-bold text-green-400">{activeAgentsCount}</div>
                            </div>
                            <div className="bg-black/80 border border-gold9/20 rounded-xl p-3 flex flex-col justify-between">
                                <div className="text-xs text-gold9/60">SUCCESS RATE</div>
                                <div className="text-2xl font-bold text-blue-400">{successRate}%</div>
                            </div>
                        </motion.div>

                        {/* FLEET COMMAND (GIT) */}
                        <motion.div
                            variants={itemVariants}
                            className="flex-1 flex flex-col gap-4 bg-black/80 border border-gold9/20 rounded-xl p-4 overflow-hidden"
                        >
                            <div className="flex items-center justify-between border-b border-gold9/10 pb-2 mb-2">
                                <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest">
                                    <GitBranch className="w-4 h-4 text-gold9" />
                                    <span className="text-gold9">FLEET COMMAND</span>
                                </h2>
                                <button
                                    onClick={handleSyncFleet}
                                    className="text-[10px] text-gold9/60 hover:text-gold9 flex items-center gap-1 border border-gold9/20 px-2 py-1 rounded hover:bg-gold9/10 transition-colors"
                                >
                                    <Activity size={10} />
                                    SYNC REPOS
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto scrollbar-hide space-y-3">
                                {fleetStatus.length === 0 ? (
                                    <div className="text-xs text-gold9/40 italic text-center py-10">
                                        No repositories under command.
                                    </div>
                                ) : (
                                    fleetStatus.map((repo, i) => (
                                        <div
                                            key={i}
                                            draggable
                                            onDragStart={(e) => handleRepoDragStart(e, repo.name)}
                                            onClick={() => setSelectedRepo(repo)}
                                            className="bg-gold9/5 border border-gold9/10 rounded p-3 relative hover:bg-gold9/10 transition-colors cursor-pointer active:cursor-grabbing hover:border-gold9/30"
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <div>
                                                    <div className="text-sm font-bold text-gold9">{repo.name}</div>
                                                    <div className="flex items-center gap-2 text-[10px] font-mono mt-1">
                                                        <span className={`text-${repo.branch === 'main' || repo.branch === 'master' ? 'gray-400' : 'green-400'}`}>
                                                            {repo.branch}
                                                        </span>
                                                        <span className="text-gold9/30">|</span>
                                                        <span className="text-gray-500">REMOTE</span>
                                                    </div>
                                                </div>
                                            </div>

                                            {repo.last_commit && (
                                                <div className="text-[10px] bg-black/80 p-2 rounded border border-white/5">
                                                    <div className="text-gold9/70 font-bold mb-0.5 truncate">{repo.last_commit.message}</div>
                                                    <div className="text-gray-500 flex justify-between">
                                                        <span>{repo.last_commit.author}</span>
                                                        <span>{new Date(repo.last_commit.date).toLocaleDateString()}</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </motion.div>

                        {/* MINI CHATBOX */}
                        <motion.div variants={itemVariants} className="h-48 flex flex-col bg-black/40 border border-gold9/20 rounded-xl overflow-hidden relative">
                            <div className="flex items-center justify-between border-b border-gold9/10 px-4 py-2 bg-gold9/5">
                                <h2 className="flex items-center gap-2 text-sm font-bold tracking-widest">
                                    <MessageSquare className="w-4 h-4 text-gold9" />
                                    <span className="text-gold9">COMM LINK</span>
                                </h2>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide mask-image-gradient">
                                {messages && messages.slice(-10).map((msg, i) => (
                                    <div key={i} className="text-sm">
                                        <span className="text-gold8 font-sans text-[10px] opacity-70">[{msg.time}]</span> <span className="font-bold text-gold9 text-xs">{msg.sender}</span>
                                        <div className="text-gray11 mt-0.5 leading-relaxed text-xs">{msg.text}</div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>
                            <div className="p-2 border-t border-gold9/10 bg-black/60 backdrop-blur-md">
                                <input
                                    type="text"
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleSend}
                                    placeholder="TRANSMIT COMMAND..."
                                    className="w-full bg-black/40 border border-gold9/30 rounded p-2 text-xs text-gold9 focus:outline-none focus:border-gold9 focus:ring-1 focus:ring-gold9/50 transition-all placeholder-gold9/50"
                                />
                            </div>
                        </motion.div>
                    </div>
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

                {/* SESSION DETAIL MODAL */}
                {selectedSession && (
                    <SessionDetailModal
                        session={selectedSession}
                        onClose={closeSessionDetails}
                        socket={socket}
                        onViewArtifact={setSelectedArtifact}
                    />
                )}

                {/* ARTIFACT MODAL */}
                {selectedArtifact && (
                    <ArtifactModal
                        artifact={selectedArtifact}
                        onClose={() => setSelectedArtifact(null)}
                    />
                )}

                {/* REPO DETAILS MODAL */}
                {selectedRepo && (
                    <RepoDetailsModal
                        repo={selectedRepo}
                        onClose={() => setSelectedRepo(null)}
                        socket={socket}
                    />
                )}

                {/* AUTOMATION EDITOR */}
                {showEditor && (
                    <AutomationEditor
                        tasks={tasks}
                        socket={socket}
                        onClose={() => setShowEditor(false)}
                    />
                )}


                {/* FLEET AGENT DETAIL MODAL */}
                {selectedFleetAgent && (
                    <div className="absolute inset-0 z-[150] bg-black/80  flex items-center justify-center p-6">
                        <div className="bg-[#111] border border-gold9/30 rounded-xl w-full max-w-md shadow-[0_0_50px_rgba(255,215,0,0.1)] flex flex-col max-h-full">
                            <div className="p-4 border-b border-gold9/20 flex justify-between items-center bg-gold9/5">
                                <h2 className="text-lg font-bold text-gold9 font-mono flex items-center gap-2">
                                    <Server size={18} />
                                    AGENT {selectedFleetAgent.id}
                                </h2>
                                <button onClick={() => setSelectedFleetAgent(null)} className="text-gray-400 hover:text-white transition-colors">
                                    <X size={20} />
                                </button>
                            </div>
                            <div className="p-6 space-y-4 font-mono text-sm">
                                <div>
                                    <span className="text-gold9/40 block text-xs mb-1">STATUS</span>
                                    <span className={`px-2 py-1 rounded text-xs ${
                                        selectedFleetAgent.status === 'working' ? 'bg-green-500/20 text-green-400' :
                                        selectedFleetAgent.status === 'stuck' || selectedFleetAgent.status === 'error' ? 'bg-red-500/20 text-red-400' :
                                        'bg-gray-500/20 text-gray-300'
                                    }`}>
                                        {selectedFleetAgent.status.toUpperCase()}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gold9/40 block text-xs mb-1">CURRENT REPO</span>
                                    <span className="text-gray-200">{selectedFleetAgent.current_repo || 'Unassigned'}</span>
                                </div>
                                <div>
                                    <span className="text-gold9/40 block text-xs mb-1">LAST ACTIVE</span>
                                    <span className="text-gray-200">{new Date(selectedFleetAgent.last_active * 1000).toLocaleString()}</span>
                                </div>
                                {selectedFleetAgent.current_task && (
                                     <div>
                                        <span className="text-gold9/40 block text-xs mb-1">CURRENT TASK</span>
                                        <span className="text-gray-200">{selectedFleetAgent.current_task}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* TASK DETAIL MODAL */}
                {selectedTask && (
                    <div className="absolute inset-0 z-[150] bg-black/80  flex items-center justify-center p-6">
                        <div className="bg-[#111] border border-gold9/30 rounded-xl w-full max-w-lg shadow-[0_0_50px_rgba(255,215,0,0.1)] flex flex-col max-h-full">
                            <div className="p-4 border-b border-gold9/20 flex justify-between items-center bg-gold9/5">
                                <h2 className="text-lg font-bold text-gold9 font-mono flex items-center gap-2">
                                    <Activity size={18} />
                                    TASK DETAILS
                                </h2>
                                <button onClick={() => setSelectedTask(null)} className="text-gray-400 hover:text-white transition-colors">
                                    <X size={20} />
                                </button>
                            </div>
                            <div className="p-6 space-y-4 font-mono text-sm overflow-y-auto scrollbar-hide select-text">
                                <div>
                                    <span className="text-gold9/40 block text-xs mb-1">PROMPT</span>
                                    <div className="text-gray-200 bg-black/80 p-3 rounded border border-white/5 whitespace-pre-wrap select-text">{selectedTask.prompt}</div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <span className="text-gold9/40 block text-xs mb-1">STATUS</span>
                                        <span className={`px-2 py-1 rounded text-xs ${
                                            selectedTask.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                                            selectedTask.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                            selectedTask.status === 'in_progress' ? 'bg-gold9/20 text-gold9' :
                                            'bg-gray-500/20 text-gray-300'
                                        }`}>
                                            {selectedTask.status.toUpperCase()}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gold9/40 block text-xs mb-1">REPO</span>
                                        <span className="text-gray-200">{selectedTask.repoName}</span>
                                    </div>
                                    <div>
                                        <span className="text-gold9/40 block text-xs mb-1">ASSIGNED AGENT</span>
                                        <span className="text-gray-200">{selectedTask.agent_id || 'None'}</span>
                                    </div>
                                     <div>
                                        <span className="text-gold9/40 block text-xs mb-1">DEPENDS ON</span>
                                        <span className="text-gray-200">{selectedTask.depends_on || 'None'}</span>
                                    </div>
                                </div>
                                {selectedTask.status === 'failed' && selectedTask.error_message && (
                                    <div className="mt-4">
                                        <span className="text-red-500/80 font-bold block text-xs mb-1 tracking-widest">FAILURE REASON</span>
                                        <div className="bg-red-500/20 text-red-400 p-3 rounded border border-red-500/30 whitespace-pre-wrap select-text font-mono text-xs">
                                            {selectedTask.error_message}
                                        </div>
                                    </div>
                                )}
                                <div className="mt-6 flex justify-end">
                                    <button
                                        onClick={() => {
                                            socket.emit('remove_task_from_queue', { repo_name: selectedTask.repoName, task_id: selectedTask.id });
                                            setSelectedTask(null);
                                        }}
                                        className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 rounded transition-colors text-xs font-bold"
                                    >
                                        CANCEL TASK
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* AUTH MODAL */}
                {showAuthModal && (
                    <div className="absolute inset-0 z-[150] bg-black/80  flex items-center justify-center">
                        <div className="bg-black border border-gold9 p-6 rounded-xl w-[400px] shadow-[0_0_50px_rgba(255,215,0,0.2)]">
                            <h2 className="text-xl font-bold text-gold9 mb-4 flex items-center gap-2">
                                <Shield size={18} />
                                AUTHENTICATION REQUIRED
                            </h2>
                            <p className="text-xs text-gold9/60 mb-4">
                                Access to one or more repositories requires a GitHub Personal Access Token (classic).
                            </p>
                            <form onSubmit={(e) => {
                                e.preventDefault();
                                const token = e.target.token.value;
                                if (socket && token) {
                                    socket.emit('save_github_token', { token });
                                    setShowAuthModal(false);
                                    // Retry sync immediately?
                                    socket.emit('sync_fleet');
                                }
                            }}>
                                <input
                                    name="token"
                                    type="password"
                                    className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none mb-4"
                                    placeholder="ghp_..."
                                    autoFocus
                                />
                                <div className="flex justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowAuthModal(false)}
                                        className="px-4 py-2 text-xs text-gold9/50 hover:text-gold9"
                                    >
                                        CANCEL
                                    </button>
                                    <button
                                        type="submit"
                                        className="px-4 py-2 bg-gold9 text-black text-xs font-bold rounded hover:bg-yellow-400"
                                    >
                                        SAVE & SYNC
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

            </motion.div>
        </AnimatePresence>
    );
};

const SessionDetailModal = ({ session, onClose, socket, onViewArtifact }) => {
    const [activities, setActivities] = useState([]);
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (socket) {
            socket.emit('get_jules_activities', { id: session.id });
            setLoading(true);

            const handleData = (data) => {
                if (data.id === session.id) {
                    setActivities(data.activities);
                    setLoading(false);
                }
            };

            socket.on('jules_activities', handleData);
            return () => socket.off('jules_activities', handleData);
        }
    }, [socket, session.id]);

    const handleSend = (e) => {
        e.preventDefault();
        if (!message.trim()) return;

        if (socket) {
            socket.emit('send_jules_message', { id: session.id, message });
            // Optimistic update
            const newMsg = {
                userMessage: { content: message },
                createTime: new Date().toISOString()
            };
            setActivities(prev => [...prev, newMsg]);
            setMessage('');
        }
    };

    const handleApprove = () => {
        if (socket) {
            socket.emit('send_jules_message', { id: session.id, message: "Plan approved. Proceed." });
        }
    };

    return (
        <div className="absolute inset-0 z-50 bg-black/80  flex items-center justify-center p-8">
            <div className="bg-black border border-gold9 rounded-xl w-full max-w-4xl h-[80vh] flex flex-col relative shadow-[0_0_50px_rgba(255,215,0,0.2)]">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-gold9/20 bg-gold9/5">
                    <div>
                        <h2 className="text-xl font-bold text-gold9 flex items-center gap-2">
                            <Terminal size={18} />
                            SESSION: {session.title || session.id}
                        </h2>
                        <div className="text-xs text-gold9/60 font-mono">ID: {session.id} | STATE: {session.state}</div>
                    </div>
                    <button onClick={onClose} className="text-gold9/50 hover:text-gold9 p-2">✕</button>
                </div>

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-black/80 scrollbar-hide">
                    {loading ? (
                        <div className="text-center text-gold9/40 py-20 animate-pulse">Initializing Uplink...</div>
                    ) : (
                        activities.length === 0 ? (
                            <div className="text-center text-gold9/40 py-20 italic">No telemetry data.</div>
                        ) : (
                            activities.map((act, i) => (
                                <ActivityItem key={i} activity={act} onViewArtifact={onViewArtifact} />
                            ))
                        )
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-gold9/20 bg-gold9/5">
                    <form onSubmit={handleSend} className="flex gap-2">
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            className="flex-1 bg-black border border-gold9/30 rounded p-3 text-gold9 focus:border-gold9 outline-none"
                            placeholder="Transmit instructions..."
                        />
                        <button type="submit" className="bg-gold9/20 border border-gold9 text-gold9 p-3 rounded hover:bg-gold9 hover:text-black transition-colors">
                            <Send size={18} />
                        </button>
                        <button type="button" onClick={handleApprove} className="bg-green-500/20 border border-green-500 text-green-400 px-4 rounded hover:bg-green-500 hover:text-black transition-colors flex items-center gap-2 text-xs font-bold tracking-widest">
                            <ThumbsUp size={14} />
                            APPROVE
                        </button>
                    </form>
                    <div className="mt-2 text-[10px] text-center text-gold9/30">
                        VOICE CHANNEL ACTIVE: Speak to inject context directly.
                    </div>
                </div>
            </div>
        </div>
    );
};

const ActivityItem = ({ activity, onViewArtifact }) => {
    // 1. Agent Message
    if (activity.agentMessage) {
        return (
            <div className="flex justify-start">
                <div className="max-w-[80%] p-4 rounded-xl border border-gold9/30 bg-gold9/5 text-gold9  shadow-[0_0_15px_rgba(255,215,0,0.05)]">
                    <div className="flex items-center gap-2 mb-2 border-b border-gold9/10 pb-1">
                        <Cpu size={12} />
                        <span className="text-[10px] font-bold tracking-widest opacity-70">JULES AGENT</span>
                        <span className="text-[10px] opacity-40 ml-auto">{new Date(activity.createTime || Date.now()).toLocaleTimeString()}</span>
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed font-mono opacity-90">
                        {activity.agentMessage.content}
                    </div>
                </div>
            </div>
        );
    }

    // 2. User Message
    if (activity.userMessage) {
        return (
            <div className="flex justify-end">
                <div className="max-w-[80%] p-4 rounded-xl border border-blue-500/30 bg-blue-500/5 text-blue-200 ">
                    <div className="flex items-center gap-2 mb-2 border-b border-blue-500/10 pb-1 justify-end">
                        <span className="text-[10px] opacity-40 mr-auto">{new Date(activity.createTime || Date.now()).toLocaleTimeString()}</span>
                        <span className="text-[10px] font-bold tracking-widest opacity-70">OPERATOR</span>
                        <Terminal size={12} />
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed font-mono opacity-90">
                        {activity.userMessage.content}
                    </div>
                </div>
            </div>
        );
    }

    // 3. Artifacts (Git Patches)
    if (activity.artifacts && activity.artifacts.length > 0) {
        return (
            <div className="flex justify-center my-4">
                <div className="w-full max-w-[90%] border border-green-500/40 bg-green-500/5 rounded-xl overflow-hidden">
                    <div className="bg-green-500/10 p-2 flex items-center justify-between border-b border-green-500/20">
                        <div className="flex items-center gap-2 text-green-400">
                            <FileCode size={16} />
                            <span className="text-xs font-bold tracking-widest">ARTIFACT GENERATED</span>
                        </div>
                        {activity.sessionCompleted && (
                            <div className="flex items-center gap-1 text-[10px] bg-green-500/20 px-2 py-0.5 rounded text-green-300">
                                <CheckCircle size={10} />
                                <span>SESSION COMPLETE</span>
                            </div>
                        )}
                    </div>
                    <div className="p-4 space-y-3">
                        {activity.artifacts.map((art, idx) => {
                            if (art.changeSet && art.changeSet.gitPatch) {
                                const patch = art.changeSet.gitPatch;
                                const messageLines = (patch.suggestedCommitMessage || "No message").split('\n');
                                const subject = messageLines[0];
                                const body = messageLines.slice(1).join('\n').trim();

                                // Source cleaning (e.g., sources/github/User/Repo -> User/Repo)
                                let source = art.changeSet.source || "Unknown Repo";
                                if (source.startsWith('sources/github/')) source = source.replace('sources/github/', '');

                                return (
                                    <div
                                        key={idx}
                                        className="space-y-2 cursor-pointer hover:bg-green-500/10 p-2 rounded transition-colors group"
                                        onClick={() => onViewArtifact && onViewArtifact({
                                            title: subject,
                                            body: body,
                                            source: source,
                                            commit: patch.baseCommitId,
                                            // Pass raw patch instructions if available in body or separate field
                                            // The API might return patch diffs too, but for now we just show message
                                        })}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="mt-1">
                                                <GitCommit size={18} className="text-green-400 group-hover:text-green-300" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-bold text-green-200 truncate group-hover:text-white" title={subject}>{subject}</div>
                                                {body && <div className="text-xs text-green-500/60 mt-1 whitespace-pre-wrap line-clamp-2">{body}</div>}
                                            </div>
                                        </div>
                                        <div className="pl-8 text-[10px] font-mono text-green-500/40 flex gap-4">
                                            <span>REPO: {source}</span>
                                            <span>COMMIT: {patch.baseCommitId ? patch.baseCommitId.substring(0, 7) : 'HEAD'}</span>
                                        </div>
                                        <div className="pl-8 text-[10px] text-green-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                            [CLICK TO INSPECT]
                                        </div>
                                    </div>
                                );
                            }
                            return <div key={idx} className="text-xs text-green-500/50 italic">Unknown Artifact Type</div>;
                        })}
                    </div>
                </div>
            </div>
        );
    }

    // 4. Plan
    if (activity.plan) {
         return (
            <div className="flex justify-center my-4">
                <div className="w-full max-w-[90%] border border-purple-500/40 bg-purple-500/5 rounded-xl p-4 shadow-[0_0_20px_rgba(168,85,247,0.1)]">
                     <div className="flex items-center gap-2 mb-3 text-purple-400 border-b border-purple-500/20 pb-2">
                        <List size={16} />
                        <span className="text-xs font-bold tracking-widest">STRATEGIC PLAN</span>
                    </div>
                    <PlanVisualizer steps={activity.plan.steps} />
                </div>
            </div>
         );
    }

    // 5. Session Completed (No Artifacts)
    if (activity.sessionCompleted) {
        return (
            <div className="flex justify-center my-4">
                 <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 px-4 py-2 rounded-full text-green-400">
                    <CheckCircle size={14} />
                    <span className="text-xs font-bold tracking-widest">MISSION COMPLETED</span>
                 </div>
            </div>
        );
    }

    // Fallback
    return (
        <div className="flex justify-center my-2 opacity-50">
            <div className="text-[10px] text-gold9 font-mono bg-gold9/5 px-2 py-1 rounded border border-gold9/10">
                RAW: {JSON.stringify(activity).substring(0, 50)}...
            </div>
        </div>
    );
};

const ArtifactModal = ({ artifact, onClose }) => {
    return (
        <div className="absolute inset-0 z-[60] bg-black/80  flex items-center justify-center p-8">
            <div className="bg-black border border-green-500/50 rounded-xl w-full max-w-3xl max-h-[80vh] flex flex-col relative shadow-[0_0_50px_rgba(0,255,0,0.1)]">
                <div className="flex justify-between items-center p-4 border-b border-green-500/20 bg-green-500/5">
                    <div>
                        <h2 className="text-lg font-bold text-green-400 flex items-center gap-2">
                            <GitCommit size={18} />
                            ARTIFACT INSPECTION
                        </h2>
                        <div className="text-xs text-green-500/60 font-mono">
                            COMMIT: {artifact.commit ? artifact.commit.substring(0, 7) : 'HEAD'} | REPO: {artifact.source}
                        </div>
                    </div>
                    <button onClick={onClose} className="text-green-500/50 hover:text-green-400 p-2">
                        <X size={20} />
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-6 scrollbar-hide text-green-200">
                    <div className="mb-4">
                        <h3 className="text-sm font-bold text-green-500 mb-1 uppercase tracking-widest">Subject</h3>
                        <div className="text-lg font-bold">{artifact.title}</div>
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-green-500 mb-2 uppercase tracking-widest">Description</h3>
                        <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed bg-green-900/10 p-4 rounded border border-green-500/10">
                            {artifact.body || "No detailed description provided."}
                        </div>
                    </div>
                </div>
                <div className="p-4 border-t border-green-500/20 bg-green-500/5 flex justify-end">
                    <button onClick={onClose} className="px-6 py-2 border border-green-500/30 hover:bg-green-500/10 text-green-400 rounded text-xs font-bold tracking-widest transition-colors">
                        CLOSE INSPECTION
                    </button>
                </div>
            </div>
        </div>
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

    // Schedule Editor State
    const [scheduleMode, setScheduleMode] = useState('daily'); // 'daily' or 'interval'
    const [intervalMinutes, setIntervalMinutes] = useState(60);
    const [dailyTime, setDailyTime] = useState('09:00');
    const [dailyDays, setDailyDays] = useState(['Mon', 'Tue', 'Wed', 'Thu', 'Fri']);

    const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    const toggleDay = (day) => {
        if (dailyDays.includes(day)) {
            setDailyDays(dailyDays.filter(d => d !== day));
        } else {
            setDailyDays([...dailyDays, day]);
        }
    };

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

        let finalTriggerValue = triggerValue;
        if (triggerType === 'schedule') {
            if (scheduleMode === 'interval') {
                finalTriggerValue = {
                    mode: 'interval',
                    interval_minutes: parseInt(intervalMinutes)
                };
            } else {
                finalTriggerValue = {
                    mode: 'daily',
                    time: dailyTime,
                    days: dailyDays
                };
            }
        }

        if (socket) {
            socket.emit('create_task', {
                title,
                trigger_type: triggerType,
                trigger_value: finalTriggerValue,
                action_type: actionType,
                action_value: finalActionValue
            });
        }
        onClose();
    };

    return (
        <div className="absolute inset-0 z-50 bg-black/80  flex items-center justify-center">
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

                    {/* SCHEDULE EDITOR */}
                    {triggerType === 'schedule' && (
                        <div className="bg-gold9/5 p-3 rounded border border-gold9/10 space-y-3">
                            <div>
                                <label className="block text-xs text-gold9/60 mb-1">FREQUENCY</label>
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setScheduleMode('daily')}
                                        className={`flex-1 py-1 text-xs border rounded ${scheduleMode === 'daily' ? 'bg-gold9 text-black border-gold9' : 'border-gold9/30 text-gold9/60'}`}
                                    >
                                        DAILY
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setScheduleMode('interval')}
                                        className={`flex-1 py-1 text-xs border rounded ${scheduleMode === 'interval' ? 'bg-gold9 text-black border-gold9' : 'border-gold9/30 text-gold9/60'}`}
                                    >
                                        INTERVAL
                                    </button>
                                </div>
                            </div>

                            {scheduleMode === 'daily' ? (
                                <div className="space-y-3">
                                    <div className="flex gap-2 items-center">
                                        <div className="flex-1">
                                            <label className="block text-[10px] text-gold9/40 mb-1">TIME (24H)</label>
                                            <input
                                                type="time"
                                                value={dailyTime}
                                                onChange={(e) => setDailyTime(e.target.value)}
                                                className="w-full bg-black border border-gold9/30 rounded p-1 text-sm text-gold9 text-center"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-[10px] text-gold9/40 mb-1">DAYS ACTIVE</label>
                                        <div className="flex justify-between">
                                            {DAYS.map(day => (
                                                <button
                                                    key={day}
                                                    type="button"
                                                    onClick={() => toggleDay(day)}
                                                    className={`w-8 h-8 rounded-full text-[10px] font-bold flex items-center justify-center border transition-colors ${
                                                        dailyDays.includes(day)
                                                            ? 'bg-gold9 text-black border-gold9'
                                                            : 'bg-transparent text-gold9/40 border-gold9/20 hover:border-gold9/50'
                                                    }`}
                                                >
                                                    {day.charAt(0)}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <label className="block text-[10px] text-gold9/40 mb-1">REPEAT EVERY (MINUTES)</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={intervalMinutes}
                                        onChange={(e) => setIntervalMinutes(e.target.value)}
                                        className="w-full bg-black border border-gold9/30 rounded p-2 text-sm text-gold9"
                                    />
                                    <div className="text-[10px] text-gold9/30 mt-1 text-right">
                                        Approx: {(intervalMinutes / 60).toFixed(1)} hours
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* OTHER TRIGGERS */}
                    {(triggerType === 'git' || triggerType === 'trello') && (
                        <div>
                            <label className="block text-xs text-gold9/60 mb-1">EVENT DETAIL</label>
                            <input
                                type="text"
                                value={triggerValue}
                                onChange={(e) => setTriggerValue(e.target.value)}
                                className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
                                placeholder={triggerType === 'git' ? 'owner/repo' : 'List Name'}
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
                                    className="w-full bg-gray-900 border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
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
                        data-testid="save-routine"
                        className="w-full bg-gold9 text-black font-bold py-2 rounded hover:bg-yellow-400 transition-colors tracking-widest mt-4"
                    >
                        {triggerType === 'manual' ? 'SAVE ROUTINE' : 'INITIALIZE ROUTINE'}
                    </button>
                </form>
            </div>
        </div>
    );
};

const RepoDetailsModal = ({ repo, onClose, socket }) => {
    const [branches, setBranches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [reviewBranch, setReviewBranch] = useState(null);
    const [autoMergeEnabled, setAutoMergeEnabled] = useState(repo.auto_merge_enabled || false);

    useEffect(() => {
        setAutoMergeEnabled(repo.auto_merge_enabled || false);
    }, [repo]);

    const handleAutoMergeToggle = () => {
        const newValue = !autoMergeEnabled;
        setAutoMergeEnabled(newValue);
        if (socket) {
            socket.emit('update_repo_config', {
                repo: repo.name,
                config: { auto_merge_enabled: newValue }
            });
        }
    };

    useEffect(() => {
        if (socket) {
            socket.emit('get_repo_branches', { repo: repo.name });
            const handleData = (data) => {
                if (data.repo === repo.name) {
                    setBranches(data.branches);
                    setLoading(false);
                }
            };
            socket.on('repo_branches', handleData);
            return () => socket.off('repo_branches', handleData);
        }
    }, [socket, repo.name]);

    if (reviewBranch) {
        return (
            <BranchReviewView
                repo={repo}
                branch={reviewBranch}
                socket={socket}
                onBack={() => setReviewBranch(null)}
                onClose={onClose}
            />
        );
    }

    return (
        <div className="absolute inset-0 z-[70] bg-black/80  flex items-center justify-center p-8">
            <div className="bg-black border border-gold9 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col relative shadow-[0_0_50px_rgba(255,215,0,0.1)]">
                <div className="flex justify-between items-center p-4 border-b border-gold9/20 bg-gold9/5">
                    <div>
                        <h2 className="text-lg font-bold text-gold9 flex items-center gap-2">
                            <GitBranch size={18} />
                            REPO: {repo.name}
                        </h2>
                        <div className="text-xs text-gold9/60 font-mono">REMOTE BRANCHES</div>
                    </div>
                    <button onClick={onClose} className="text-gold9/50 hover:text-gold9 p-2">✕</button>
                </div>

                <div className="p-4 border-b border-gold9/10 bg-black">
                    <div className="text-sm font-bold text-gold9 mb-2 uppercase tracking-widest">Allowed Actions</div>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoMergeEnabled}
                            onChange={handleAutoMergeToggle}
                            className="accent-gold9 bg-black border-gold9"
                        />
                        <span className="text-xs text-gold9/80">Allow Smart Auto-Merge</span>
                    </label>
                </div>

                <div className="flex-1 overflow-y-auto p-4 scrollbar-hide space-y-2">
                    {loading ? (
                        <div className="text-center text-gold9/40 py-10 animate-pulse">Scanning Remote Refs...</div>
                    ) : (
                        branches.map((b, i) => (
                            <div key={i} className="flex justify-between items-center bg-gold9/5 p-3 rounded border border-gold9/10 hover:bg-gold9/10 transition-colors">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-gold9">{b.name}</span>
                                        {b.is_default && <span className="text-[10px] bg-gold9/20 px-2 rounded text-gold9">DEFAULT</span>}
                                    </div>
                                    <div className="text-[10px] text-gold9/50 flex gap-3 mt-1">
                                        <span className={b.ahead > 0 ? "text-green-400" : ""}>{b.ahead} commits ahead</span>
                                        <span className={b.behind > 0 ? "text-red-400" : ""}>{b.behind} commits behind</span>
                                    </div>
                                </div>
                                {!b.is_default && b.ahead > 0 && (
                                    <button
                                        onClick={() => setReviewBranch(b.name)}
                                        className="bg-green-500/20 hover:bg-green-500/40 text-green-400 border border-green-500/50 rounded px-3 py-1 text-xs font-bold tracking-widest transition-all flex items-center gap-1"
                                    >
                                        <CheckSquare size={12} />
                                        REVIEW
                                    </button>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

const BranchReviewView = ({ repo, branch, socket, onBack, onClose }) => {
    const [diffData, setDiffData] = useState(null);
    const [selectedFile, setSelectedFile] = useState(null);
    const [merging, setMerging] = useState(false);

    useEffect(() => {
        if (socket) {
            socket.emit('get_branch_diff', { repo: repo.name, branch: branch });
            const handleDiff = (data) => {
                if (data.repo === repo.name && data.branch === branch) {
                    setDiffData(data);
                    if (data.files && data.files.length > 0) {
                        setSelectedFile(data.files[0]);
                    }
                }
            };
            socket.on('branch_diff_data', handleDiff);
            return () => socket.off('branch_diff_data', handleDiff);
        }
    }, [socket, repo.name, branch]);

    const handleApproveAndMerge = () => {
        if (confirm("Are you sure? This will merge the branch into main and DELETE the remote branch.")) {
            setMerging(true);
            socket.emit('perform_git_merge', {
                repo: repo.name,
                branch: branch,
                target: diffData?.target || 'main',
                delete_source_branch: true
            });
            setTimeout(() => {
                onClose();
            }, 1000);
        }
    };

    if (!diffData) {
        return (
            <div className="absolute inset-0 z-[75] bg-black/90 flex items-center justify-center text-gold9">
                <div className="animate-pulse flex flex-col items-center gap-2">
                    <Activity size={24} />
                    <span className="text-xs font-mono tracking-widest">FETCHING DIFF CONTEXT...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="absolute inset-0 z-[70] bg-black/80  flex items-center justify-center p-4">
            <div className="bg-black border border-gold9 rounded-xl w-full max-w-6xl h-[90vh] flex flex-col relative shadow-[0_0_50px_rgba(255,215,0,0.1)]">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-gold9/20 bg-gold9/5">
                    <div>
                        <h2 className="text-lg font-bold text-gold9 flex items-center gap-2">
                            <CheckSquare size={18} />
                            CODE REVIEW: {branch}
                        </h2>
                        <div className="text-xs text-gold9/60 font-mono">
                            TARGET: {diffData.target} | FILES CHANGED: {diffData.files.length}
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={onBack} className="px-3 py-1 text-xs text-gold9/60 border border-gold9/20 rounded hover:bg-gold9/10">
                            BACK
                        </button>
                        <button onClick={onClose} className="text-gold9/50 hover:text-gold9 p-2">✕</button>
                    </div>
                </div>

                {/* Content Split */}
                <div className="flex-1 flex min-h-0 overflow-hidden">
                    {/* Left: File List */}
                    <div className="w-1/3 border-r border-gold9/20 flex flex-col bg-black/80">
                        <div className="p-2 border-b border-gold9/10 text-xs font-bold text-gold9/40 tracking-widest uppercase">
                            Changed Files
                        </div>
                        <div className="flex-1 overflow-y-auto scrollbar-hide">
                            {diffData.files.map((file, i) => (
                                <div
                                    key={i}
                                    onClick={() => setSelectedFile(file)}
                                    className={`p-3 text-sm font-mono cursor-pointer border-l-2 transition-colors flex justify-between items-center ${
                                        selectedFile && selectedFile.filename === file.filename
                                            ? 'border-gold9 bg-gold9/10 text-gold9'
                                            : 'border-transparent text-gray-400 hover:text-gold9/80 hover:bg-gold9/5'
                                    }`}
                                >
                                    <span className="truncate flex-1 mr-2" title={file.filename}>{file.filename}</span>
                                    <div className="flex gap-2 text-[10px]">
                                        <span className="text-green-400">+{file.additions}</span>
                                        <span className="text-red-400">-{file.deletions}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Right: Diff Viewer */}
                    <div className="w-2/3 flex flex-col bg-[#1e1e1e]">
                         <div className="p-2 border-b border-white/10 text-xs font-bold text-gray-400 flex justify-between">
                            <span>{selectedFile ? selectedFile.filename : 'No file selected'}</span>
                         </div>
                         <div className="flex-1 overflow-y-auto overflow-x-auto p-4 font-mono text-xs text-gray-300 scrollbar-hide">
                            {selectedFile && selectedFile.patch ? (
                                <pre className="whitespace-pre">{selectedFile.patch}</pre>
                            ) : (
                                <div className="text-gray-600 italic mt-10 text-center">
                                    {selectedFile ? (selectedFile.status === 'added' ? '(New File)' : '(Binary or Large File)') : 'Select a file to view diff'}
                                </div>
                            )}
                         </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t border-gold9/20 bg-gold9/5 flex justify-between items-center">
                    <div className="text-xs text-gold9/40">
                        CAUTION: Merging will immediately trigger deployment and delete source branch.
                    </div>
                    <button
                        onClick={handleApproveAndMerge}
                        disabled={merging}
                        className={`px-6 py-2 rounded text-black font-bold tracking-widest flex items-center gap-2 transition-all ${
                            merging ? 'bg-green-500/50 cursor-wait' : 'bg-green-500 hover:bg-green-400 shadow-[0_0_15px_rgba(34,197,94,0.4)]'
                        }`}
                    >
                        <ThumbsUp size={16} />
                        {merging ? 'MERGING...' : 'APPROVE & MERGE'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default WarRoomDashboard;
