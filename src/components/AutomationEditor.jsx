import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Save,
    X,
    Plus,
    Play,
    Trash2,
    Zap,
    GitBranch,
    Clock,
    Layout,
    Terminal,
    MessageSquare,
    Bell,
    CheckSquare,
    Cpu,
    ArrowRight
} from 'lucide-react';

const AutomationEditor = ({ tasks, socket, onClose }) => {
    const [selectedTaskId, setSelectedTaskId] = useState(null);
    const [draftTask, setDraftTask] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null); // 'trigger' | 'action'
    // --- INITIALIZATION ---

    // Load task into draft when selected
    useEffect(() => {
        if (selectedTaskId) {
            const task = tasks.find(t => t.id === selectedTaskId);
            if (task) {
                setDraftTask(JSON.parse(JSON.stringify(task))); // Deep copy
            }
        } else {
            // New Task Template
            setDraftTask({
                title: "New Automation",
                trigger: { type: "manual", value: null },
                action: { type: "notify", value: "" },
                status: "active"
            });
        }
        setSelectedNode(null);
    }, [selectedTaskId, tasks]);

    const handleSave = () => {
        if (!draftTask) return;
        if (!draftTask.title.trim()) {
            alert("Please provide a title.");
            return;
        }

        if (selectedTaskId) {
            // Update
            socket.emit('update_task', {
                id: selectedTaskId,
                updates: {
                    title: draftTask.title,
                    trigger: draftTask.trigger,
                    action: draftTask.action,
                    status: draftTask.status
                }
            });
        } else {
            // Create
            socket.emit('create_task', {
                title: draftTask.title,
                trigger_type: draftTask.trigger.type,
                trigger_value: draftTask.trigger.value,
                action_type: draftTask.action.type,
                action_value: draftTask.action.value
            });
            // Ideally we switch to the new ID, but we don't know it yet.
            // For now, just reset to new.
            setSelectedTaskId(null);
        }
    };

    const handleDelete = (e, id) => {
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this automation?")) {
            socket.emit('delete_task', { id });
            if (selectedTaskId === id) setSelectedTaskId(null);
        }
    };

    const updateDraft = (path, value) => {
        if (!draftTask) return;
        const newDraft = { ...draftTask };

        // Simple path navigation (e.g. 'trigger.type')
        const parts = path.split('.');
        let current = newDraft;
        for (let i = 0; i < parts.length - 1; i++) {
            current = current[parts[i]];
        }
        current[parts[parts.length - 1]] = value;

        // If type changed, reset value container if needed?
        // For UX simplicity we keep it but might be garbage.

        setDraftTask(newDraft);
    };

    return (
        <div className="fixed inset-0 z-[110] bg-[#0a0a0a] text-gold9 font-mono flex flex-col">
            {/* HEADER */}
            <div className="h-16 border-b border-gold9/20 flex items-center justify-between px-6 bg-black/80 ">
                <div className="flex items-center gap-4">
                    <div className="bg-gold9/10 p-2 rounded">
                        <Cpu className="text-gold9" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold tracking-[0.2em] text-gold9">AUTOMATION ENGINEER</h1>
                        <div className="text-[10px] text-gold9/50">VISUAL WORKFLOW EDITOR</div>
                    </div>
                </div>
                <div className="flex gap-4">
                     <button
                        onClick={onClose}
                        className="px-4 py-2 text-gold9/50 hover:text-gold9 border border-transparent hover:border-gold9/30 rounded transition-all flex items-center gap-2 text-xs"
                    >
                        <X size={16} /> EXIT
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* LEFT SIDEBAR: LIST */}
                <div className="w-64 border-r border-gold9/20 flex flex-col bg-black/80">
                    <button
                        onClick={() => setSelectedTaskId(null)}
                        className={`p-4 border-b border-gold9/10 flex items-center gap-2 hover:bg-gold9/10 transition-colors ${!selectedTaskId ? 'bg-gold9/20 text-white' : 'text-gold9/60'}`}
                    >
                        <Plus size={16} />
                        <span className="font-bold tracking-widest text-sm">NEW ROUTINE</span>
                    </button>
                    <div className="flex-1 overflow-y-auto">
                        {tasks.map(task => (
                            <div
                                key={task.id}
                                onClick={() => setSelectedTaskId(task.id)}
                                className={`p-4 border-b border-gold9/5 cursor-pointer group flex justify-between items-center ${selectedTaskId === task.id ? 'bg-gold9/10 border-l-2 border-l-gold9' : 'hover:bg-gold9/5 border-l-2 border-l-transparent'}`}
                            >
                                <div>
                                    <div className={`text-sm font-bold ${selectedTaskId === task.id ? 'text-gold9' : 'text-gold9/70'}`}>{task.title}</div>
                                    <div className="text-[10px] text-gold9/40 mt-1 flex gap-2">
                                        <span>{task.trigger?.type.toUpperCase()}</span>
                                        <span>→</span>
                                        <span>{task.action?.type.toUpperCase()}</span>
                                    </div>
                                </div>
                                <button onClick={(e) => handleDelete(e, task.id)} className="opacity-0 group-hover:opacity-100 text-gold9/30 hover:text-red-500 transition-all">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* CENTER: CANVAS */}
                <div className="flex-1 bg-[#111] relative overflow-hidden group">
                    {/* Grid Background */}
                    <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
                        backgroundImage: 'linear-gradient(rgba(255, 215, 0, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 215, 0, 0.2) 1px, transparent 1px)',
                        backgroundSize: '40px 40px'
                    }}></div>

                    {draftTask ? (
                        <NodeCanvas
                            task={draftTask}
                            selectedNode={selectedNode}
                            onSelectNode={setSelectedNode}
                        />
                    ) : (
                        <div className="flex items-center justify-center h-full text-gold9/20">
                            Select a task to edit
                        </div>
                    )}

                    {/* Overlay Title Editor */}
                    {draftTask && (
                        <div className="absolute top-6 left-6 z-10">
                            <label className="text-[10px] text-gold9/40 block mb-1 tracking-widest">ROUTINE NAME</label>
                            <input
                                type="text"
                                value={draftTask.title}
                                onChange={(e) => updateDraft('title', e.target.value)}
                                className="bg-transparent text-2xl font-bold text-gold9 focus:outline-none border-b border-transparent focus:border-gold9/50 pb-1 w-[400px]"
                                placeholder="Untitled Routine"
                            />
                        </div>
                    )}

                    {/* Save Action */}
                    <div className="absolute top-6 right-6 z-10">
                         <button
                            onClick={handleSave}
                            className="bg-gold9 text-black px-6 py-3 rounded font-bold tracking-widest hover:bg-yellow-400 shadow-[0_0_20px_rgba(255,215,0,0.3)] transition-all flex items-center gap-2"
                        >
                            <Save size={18} />
                            SAVE ROUTINE
                        </button>
                    </div>
                </div>

                {/* RIGHT SIDEBAR: INSPECTOR */}
                <div className="w-80 border-l border-gold9/20 bg-black/80 p-6 overflow-y-auto ">
                    <h2 className="text-xs font-bold text-gold9/40 tracking-[0.2em] mb-6 border-b border-gold9/10 pb-2">PROPERTIES</h2>

                    {selectedNode === 'trigger' && draftTask && (
                        <div className="space-y-6 animate-in slide-in-from-right-10 fade-in duration-300">
                            <div className="flex items-center gap-2 text-gold9 mb-2">
                                <Zap size={18} />
                                <span className="font-bold text-lg">TRIGGER</span>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-gold9/60 block mb-2">TYPE</label>
                                    <select
                                        value={draftTask.trigger.type}
                                        onChange={(e) => updateDraft('trigger.type', e.target.value)}
                                        className="w-full bg-black/80 border border-gold9/30 rounded p-3 text-sm text-gold9 focus:border-gold9 outline-none"
                                    >
                                        <option value="manual">MANUAL (Button)</option>
                                        <option value="schedule">SCHEDULE (Time/Interval)</option>
                                        <option value="git">GIT EVENT (Commit/PR)</option>
                                        <option value="trello">TRELLO (Card Move)</option>
                                    </select>
                                </div>

                                {/* Dynamic Fields based on Trigger Type */}
                                {draftTask.trigger.type === 'schedule' && (
                                    <ScheduleEditor
                                        value={draftTask.trigger.value || {}}
                                        onChange={(v) => updateDraft('trigger.value', v)}
                                    />
                                )}

                                {draftTask.trigger.type === 'git' && (
                                    <div>
                                        <label className="text-xs text-gold9/60 block mb-2">REPO (Owner/Name)</label>
                                        <input
                                            type="text"
                                            value={draftTask.trigger.value || ''}
                                            onChange={(e) => updateDraft('trigger.value', e.target.value)}
                                            className="w-full bg-black/80 border border-gold9/30 rounded p-3 text-sm text-gold9 focus:border-gold9 outline-none"
                                            placeholder="owner/repo"
                                        />
                                        <div className="text-[10px] text-gold9/40 mt-1">Leave empty to match all monitored repos.</div>
                                    </div>
                                )}

                                {draftTask.trigger.type === 'trello' && (
                                    <div>
                                        <label className="text-xs text-gold9/60 block mb-2">LIST NAME</label>
                                        <input
                                            type="text"
                                            value={draftTask.trigger.value || ''}
                                            onChange={(e) => updateDraft('trigger.value', e.target.value)}
                                            className="w-full bg-black/80 border border-gold9/30 rounded p-3 text-sm text-gold9 focus:border-gold9 outline-none"
                                            placeholder="Done"
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {selectedNode === 'action' && draftTask && (
                        <div className="space-y-6 animate-in slide-in-from-right-10 fade-in duration-300">
                             <div className="flex items-center gap-2 text-blue-400 mb-2">
                                <Play size={18} />
                                <span className="font-bold text-lg">ACTION</span>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-gold9/60 block mb-2">TYPE</label>
                                    <select
                                        value={draftTask.action.type}
                                        onChange={(e) => updateDraft('action.type', e.target.value)}
                                        className="w-full bg-black/80 border border-gold9/30 rounded p-3 text-sm text-gold9 focus:border-gold9 outline-none"
                                    >
                                        <option value="notify">NOTIFICATION</option>
                                        <option value="run_script">RUN SCRIPT</option>
                                    </select>
                                </div>

                                {(draftTask.action.type === 'notify' || draftTask.action.type === 'run_script') && (
                                    <div>
                                        <label className="text-xs text-gold9/60 block mb-2">VALUE</label>
                                        <input
                                            type="text"
                                            value={draftTask.action.value || ''}
                                            onChange={(e) => updateDraft('action.value', e.target.value)}
                                            className="w-full bg-black/80 border border-gold9/30 rounded p-3 text-sm text-gold9 focus:border-gold9 outline-none"
                                            placeholder={draftTask.action.type === 'notify' ? "Message to display" : "Path to script"}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {!selectedNode && draftTask && (
                        <div className="text-center text-gold9/40 py-10 italic text-xs">
                            Select a node on the canvas to edit its properties.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const NodeCanvas = ({ task, selectedNode, onSelectNode }) => {
    // We visualize a simple 2-node graph: Trigger -> Action
    // Positions
    const triggerPos = { x: 200, y: 300 };
    const actionPos = { x: 600, y: 300 };

    // Bezier Curve
    const pathD = `M ${triggerPos.x + 150} ${triggerPos.y + 40} C ${triggerPos.x + 300} ${triggerPos.y + 40}, ${actionPos.x - 150} ${actionPos.y + 40}, ${actionPos.x} ${actionPos.y + 40}`;

    return (
        <div className="w-full h-full relative" onClick={() => onSelectNode(null)}>
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#4ade80" />
                    </marker>
                </defs>
                <path
                    d={pathD}
                    fill="none"
                    stroke="#4ade80"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                    className="animate-dash"
                    markerEnd="url(#arrowhead)"
                />
            </svg>

            {/* TRIGGER NODE */}
            <div
                onClick={(e) => { e.stopPropagation(); onSelectNode('trigger'); }}
                className={`absolute w-[200px] h-[100px] bg-black border-2 rounded-xl flex items-center justify-center cursor-pointer transition-all hover:scale-105 ${selectedNode === 'trigger' ? 'border-gold9 shadow-[0_0_30px_rgba(255,215,0,0.3)]' : 'border-gold9/30 hover:border-gold9'}`}
                style={{ left: triggerPos.x, top: triggerPos.y }}
            >
                <div className="absolute -top-3 left-4 bg-[#0a0a0a] px-2 text-[10px] font-bold tracking-widest text-gold9">TRIGGER</div>
                <div className="text-center">
                    <Zap size={24} className="mx-auto mb-2 text-gold9" />
                    <div className="text-sm font-bold text-gold9">{task.trigger.type.toUpperCase()}</div>
                    <div className="text-[10px] text-gold9/50 truncate max-w-[150px] mx-auto">
                        {JSON.stringify(task.trigger.value || "Configured")}
                    </div>
                </div>
                {/* Output Port */}
                <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-gold9 rounded-full border-2 border-black"></div>
            </div>

            {/* ACTION NODE */}
             <div
                onClick={(e) => { e.stopPropagation(); onSelectNode('action'); }}
                className={`absolute w-[200px] h-[100px] bg-black border-2 rounded-xl flex items-center justify-center cursor-pointer transition-all hover:scale-105 ${selectedNode === 'action' ? 'border-blue-400 shadow-[0_0_30px_rgba(96,165,250,0.3)]' : 'border-blue-500/30 hover:border-blue-400'}`}
                style={{ left: actionPos.x, top: actionPos.y }}
            >
                <div className="absolute -top-3 left-4 bg-[#0a0a0a] px-2 text-[10px] font-bold tracking-widest text-blue-400">ACTION</div>
                 <div className="text-center">
                    <Play size={24} className="mx-auto mb-2 text-blue-400" />
                    <div className="text-sm font-bold text-blue-200">{task.action.type.toUpperCase()}</div>
                    <div className="text-[10px] text-blue-400/50 truncate max-w-[150px] mx-auto">
                         {task.action.value}
                    </div>
                </div>
                 {/* Input Port */}
                <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-400 rounded-full border-2 border-black"></div>
            </div>
        </div>
    );
};

const ScheduleEditor = ({ value, onChange }) => {
    // value: { mode: 'daily'|'interval', time, days, interval_minutes }
    const mode = value.mode || 'daily';
    const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    const update = (k, v) => onChange({ ...value, [k]: v });

    return (
        <div className="bg-gold9/5 p-3 rounded border border-gold9/10 space-y-3">
             <div className="flex gap-2">
                <button
                    onClick={() => update('mode', 'daily')}
                    className={`flex-1 py-1 text-[10px] font-bold border rounded transition-colors ${mode === 'daily' ? 'bg-gold9 text-black border-gold9' : 'border-gold9/30 text-gold9/60'}`}
                >
                    DAILY
                </button>
                <button
                    onClick={() => update('mode', 'interval')}
                    className={`flex-1 py-1 text-[10px] font-bold border rounded transition-colors ${mode === 'interval' ? 'bg-gold9 text-black border-gold9' : 'border-gold9/30 text-gold9/60'}`}
                >
                    INTERVAL
                </button>
            </div>

            {mode === 'daily' ? (
                <div className="space-y-3">
                    <div>
                        <label className="text-[10px] text-gold9/40 block mb-1">TIME (24H)</label>
                        <input
                            type="time"
                            value={value.time || '09:00'}
                            onChange={(e) => update('time', e.target.value)}
                            className="w-full bg-black border border-gold9/30 rounded p-2 text-sm text-gold9 text-center focus:border-gold9 outline-none"
                        />
                    </div>
                    <div>
                        <label className="text-[10px] text-gold9/40 block mb-1">ACTIVE DAYS</label>
                        <div className="flex justify-between">
                            {DAYS.map(day => (
                                <button
                                    key={day}
                                    onClick={() => {
                                        const days = value.days || [];
                                        if (days.includes(day)) update('days', days.filter(d => d !== day));
                                        else update('days', [...days, day]);
                                    }}
                                    className={`w-8 h-8 rounded-full text-[10px] font-bold flex items-center justify-center border transition-colors ${
                                        (value.days || []).includes(day)
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
                    <label className="text-[10px] text-gold9/40 block mb-1">EVERY (MINUTES)</label>
                    <input
                        type="number"
                        min="1"
                        value={value.interval_minutes || 60}
                        onChange={(e) => update('interval_minutes', parseInt(e.target.value))}
                        className="w-full bg-black border border-gold9/30 rounded p-2 text-sm text-gold9 focus:border-gold9 outline-none"
                    />
                </div>
            )}
        </div>
    );
};

export default AutomationEditor;
