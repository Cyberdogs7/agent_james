import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Layers, Activity, AlertTriangle, Plus, ChevronRight, Server, Play, Clock, Inbox } from 'lucide-react';

const FleetManagerUI = ({ fleetState, julesSessions = [], onAssign, onUnassign, onAddTask, onRemoveTask, onClearCompleted }) => {
    const { agents = [], repos = [] } = fleetState || {};

    // Derived state
    const unassignedAgents = agents.filter(a => !a.current_repo);
    const idleCount = agents.filter(a => a.status === 'idle').length;
    const workingCount = agents.filter(a => a.status === 'working').length;
    const stuckCount = agents.filter(a => a.status === 'stuck' || a.status === 'error').length;

    // Drag and Drop State
    const [draggedAgentId, setDraggedAgentId] = useState(null);

    const handleDragStart = (e, agentId) => {
        setDraggedAgentId(agentId);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', agentId);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = (e, repoName) => {
        e.preventDefault();
        const agentId = e.dataTransfer.getData('text/plain');
        if (agentId && repoName) {
            onAssign(agentId, repoName);
        }
        setDraggedAgentId(null);
    };

    const handleUnassignDrop = (e) => {
        e.preventDefault();
        const agentId = e.dataTransfer.getData('text/plain');
        if (agentId) {
            onUnassign(agentId);
        }
        setDraggedAgentId(null);
    };

    const [newTaskPrompts, setNewTaskPrompts] = useState({});
    const [newTaskDependencies, setNewTaskDependencies] = useState({});

    const handleAddTask = (repoName) => {
        const prompt = newTaskPrompts[repoName];
        const dependsOn = newTaskDependencies[repoName];
        if (prompt && prompt.trim()) {
            onAddTask(repoName, prompt.trim(), dependsOn);
            setNewTaskPrompts(prev => ({ ...prev, [repoName]: '' }));
            setNewTaskDependencies(prev => ({ ...prev, [repoName]: '' }));
        }
    };

    const formatTime = (ts) => {
        const diff = Math.floor(Date.now() / 1000) - ts;
        if (diff < 60) return `${diff}s`;
        if (diff < 3600) return `${Math.floor(diff/60)}m`;
        return `${Math.floor(diff/3600)}h ${Math.floor((diff%3600)/60)}m`;
    };

    const AgentPill = ({ agent, draggable = true }) => {
        let statusColor = 'bg-gray-500';
        let statusGlow = '';
        if (agent.status === 'working') {
            statusColor = 'bg-green-500';
            statusGlow = 'animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]';
        } else if (agent.status === 'stuck' || agent.status === 'error') {
            statusColor = 'bg-red-500';
            statusGlow = 'shadow-[0_0_10px_rgba(239,68,68,0.5)]';
        }

        return (
            <div
                draggable={draggable}
                onDragStart={(e) => draggable && handleDragStart(e, agent.id)}
                className={`flex items-center justify-between p-2 mb-2 rounded bg-black/40 border border-gold9/20 hover:border-gold9 cursor-grab active:cursor-grabbing transition-colors ${draggedAgentId === agent.id ? 'opacity-50' : ''}`}
            >
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${statusColor} ${statusGlow}`} />
                    <span className="text-sm font-mono text-gray-100">{agent.id.replace('agent_', 'A-')}</span>
                </div>
                <div className="text-[10px] text-gray-300 font-mono">
                    {agent.status.toUpperCase()}
                </div>
            </div>
        );
    };

    return (
        <div className="flex h-full w-full bg-transparent text-gray-100 font-sans">

            {/* Sidebar: Agent Pool */}
            <div
                className="w-64 bg-black/20 border-r border-gold9/20 flex flex-col"
                onDragOver={handleDragOver}
                onDrop={handleUnassignDrop}
            >
                <div className="p-4 border-b border-gold9/20">
                    <h2 className="text-lg font-bold font-mono tracking-widest text-gold9 flex items-center gap-2">
                        <Layers size={18} />
                        AGENT POOL
                    </h2>
                    <div className="flex justify-between mt-4 text-xs font-mono text-gray-300">
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-gray-500"/> {idleCount} IDLE</span>
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-green-500"/> {workingCount} WRK</span>
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-red-500"/> {stuckCount} ERR</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 scrollbar-hide">
                    <div className="text-xs font-bold text-gold9/40 mb-3 tracking-widest">UNASSIGNED</div>
                    {unassignedAgents.map(agent => (
                        <AgentPill key={agent.id} agent={agent} />
                    ))}
                    {unassignedAgents.length === 0 && (
                        <div className="text-center text-sm text-gold9/40 py-10 font-mono italic">
                            All agents assigned.
                        </div>
                    )}
                </div>
            </div>

            {/* Main Area: Repository Rooms */}
            <div className="flex-1 overflow-y-auto p-6 bg-transparent">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-white font-mono">KINETIC COMMAND</h1>
                        <p className="text-gold9/60 text-sm mt-1">Drag agents from the pool to allocate resources.</p>
                    </div>
                    {/* Could add a 'New Repo' button here later */}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                    {repos.map(repo => {
                        const repoAgents = agents.filter(a => a.current_repo === repo.name);

                        return (
                            <motion.div
                                layoutId={repo.name}
                                key={repo.name}
                                className="bg-black/20 border border-gold9/20 rounded-lg overflow-hidden flex flex-col shadow-xl"
                                onDragOver={handleDragOver}
                                onDrop={(e) => handleDrop(e, repo.name)}
                            >
                                {/* Repo Header */}
                                <div className="p-4 bg-gold9/5 border-b border-gold9/10 flex justify-between items-center">
                                    <h3 className="font-bold text-gold9 font-mono flex items-center gap-2">
                                        <Server size={16} />
                                        {repo.name}
                                    </h3>
                                    <div className="text-xs text-gold9/60 font-mono">
                                        {repoAgents.length} AGENTS
                                    </div>
                                </div>

                                {/* Active Agents in Repo */}
                                <div className="p-4 border-b border-gold9/20 min-h-[100px] bg-black/40">
                                    <div className="text-[10px] font-bold text-gold9/40 mb-2 tracking-widest">ASSIGNED UNIT</div>
                                    <div className="flex flex-wrap gap-2">
                                        {repoAgents.map(agent => (
                                            <div
                                                key={agent.id}
                                                draggable
                                                onDragStart={(e) => handleDragStart(e, agent.id)}
                                                className={`px-2 py-1 rounded bg-gold9/5 border border-gold9/20 flex items-center gap-2 text-xs font-mono cursor-grab hover:border-gold9 ${agent.status === 'working' ? 'shadow-[0_0_8px_rgba(255,215,0,0.15)] border-gold9/30' : ''}`}
                                            >
                                                <div className={`w-1.5 h-1.5 rounded-full ${agent.status === 'working' ? 'bg-gold9 animate-pulse' : (agent.status === 'stuck' ? 'bg-red-500' : 'bg-gray-500')}`} />
                                                <span>{agent.id.replace('agent_', 'A-')}</span>
                                                {agent.status === 'working' && (
                                                    <span className="text-[9px] text-gold9 ml-1">{formatTime(agent.last_active)}</span>
                                                )}
                                            </div>
                                        ))}
                                        {repoAgents.length === 0 && (
                                            <div className="w-full text-center py-4 border border-dashed border-gold9/10 rounded text-gold9/40 text-xs font-mono">
                                                DROP AGENT HERE
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Task Queue */}
                                <div className="p-4 flex-1 flex flex-col bg-black/20">
                                    <div className="text-[10px] font-bold text-gold9/40 mb-3 tracking-widest flex justify-between items-center">
                                        <span>TASK QUEUE ({repo.queue?.length || 0})</span>
                                        {repo.queue?.some(t => t.status === 'completed') && (
                                            <button
                                                onClick={() => onClearCompleted && onClearCompleted(repo.name)}
                                                className="text-[9px] bg-gold9/5 hover:bg-[#2A2A2A] text-gold9/60 px-2 py-1 rounded transition-colors"
                                            >
                                                CLEAR COMPLETED
                                            </button>
                                        )}
                                    </div>

                                    <div className="flex flex-col gap-2 mb-4">
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                value={newTaskPrompts[repo.name] || ''}
                                                onChange={(e) => setNewTaskPrompts({...newTaskPrompts, [repo.name]: e.target.value})}
                                                onKeyDown={(e) => e.key === 'Enter' && handleAddTask(repo.name)}
                                                placeholder="Assign new task..."
                                                className="flex-1 bg-transparent border-b-2 border-gold9/20 focus:border-gold9 text-sm text-gray-100 font-mono px-3 py-2 outline-none transition-colors placeholder-[#474746]"
                                            />
                                            <button
                                                onClick={() => handleAddTask(repo.name)}
                                                className="bg-gold9/10 text-gold9 border border-gold9/30 hover:bg-gold9 hover:text-black p-2 rounded transition-all"
                                            >
                                                <Plus size={18} />
                                            </button>
                                        </div>
                                        {repo.queue?.length > 0 && (
                                            <select
                                                value={newTaskDependencies[repo.name] || ''}
                                                onChange={(e) => setNewTaskDependencies({...newTaskDependencies, [repo.name]: e.target.value})}
                                                className="bg-transparent text-xs font-mono text-gold9/60 border border-gold9/20 rounded p-1 outline-none"
                                            >
                                                <option value="">No dependencies</option>
                                                {repo.queue.map(t => (
                                                    <option key={t.id} value={t.id}>
                                                        Depends on: {t.prompt.substring(0, 30)}{t.prompt.length > 30 ? '...' : ''}
                                                    </option>
                                                ))}
                                            </select>
                                        )}
                                    </div>

                                    <div className="flex-1 overflow-y-auto space-y-2 max-h-48 scrollbar-hide">
                                        {repo.queue?.map((task, i) => {
                                            let taskBorder = 'border-transparent';
                                            let taskBg = 'bg-gold9/5';
                                            let statusText = 'PENDING';
                                            let textStyle = 'text-gray-300';

                                            if (task.status === 'in_progress') {
                                                taskBorder = 'border-gold9/30';
                                                taskBg = 'bg-gold9/5';
                                                statusText = `IN PROGRESS (${task.agent_id ? task.agent_id.replace('agent_', 'A-') : ''})`;
                                            } else if (task.status === 'completed') {
                                                taskBorder = 'border-green-500/30';
                                                taskBg = 'bg-green-500/5';
                                                statusText = 'COMPLETED';
                                                textStyle = 'text-green-500/70 line-through';
                                            } else if (task.status === 'failed') {
                                                taskBorder = 'border-red-500/30';
                                                taskBg = 'bg-red-500/5';
                                                statusText = 'FAILED';
                                            }

                                            // Find dependency label
                                            let dependencyLabel = null;
                                            if (task.depends_on) {
                                                const depTask = repo.queue.find(t => t.id === task.depends_on);
                                                if (depTask) {
                                                    dependencyLabel = `Depends on: ${depTask.prompt.substring(0, 20)}...`;
                                                }
                                            }

                                            return (
                                                <div key={task.id} className={`group flex justify-between items-start p-2 rounded ${taskBg} border ${taskBorder} hover:border-gold9/10 transition-colors`}>
                                                    <div className="flex items-start gap-2 flex-1">
                                                        <div className="text-gold9/40 font-mono text-[10px] mt-0.5 w-4">{i+1}.</div>
                                                        <div className="flex flex-col">
                                                            <div className={`text-xs ${textStyle} line-clamp-2`}>{task.prompt}</div>
                                                            <div className="flex gap-2 mt-1">
                                                                <span className="text-[9px] font-mono text-gold9/60">{statusText}</span>
                                                                {dependencyLabel && <span className="text-[9px] font-mono text-orange-500/50">{dependencyLabel}</span>}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => onRemoveTask(repo.name, task.id)}
                                                        className="opacity-0 group-hover:opacity-100 text-red-500/50 hover:text-red-500 transition-opacity p-1"
                                                    >
                                                        <Plus size={14} className="rotate-45" />
                                                    </button>
                                                </div>
                                            );
                                        })}
                                        {(!repo.queue || repo.queue.length === 0) && (
                                            <div className="flex flex-col items-center justify-center text-gold9/40 py-6 opacity-50">
                                                <Inbox size={24} className="mb-2" />
                                                <div className="text-xs font-mono">QUEUE EMPTY</div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        )
                    })}
                </div>
            </div>
        </div>
    );
};

export default FleetManagerUI;
