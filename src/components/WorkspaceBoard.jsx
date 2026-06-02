import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Play, AlertCircle, FileText, CheckCircle, Clock, Layers } from 'lucide-react';

const LANE_CONFIG = [
  { id: 'backlog', title: 'Backlog', color: 'border-gray-500/50' },
  { id: 'todo_planning', title: 'Todo / Planning', color: 'border-blue-500/50' },
  { id: 'dev_implementation', title: 'Dev / Implementation', color: 'border-purple-500/50' },
  { id: 'review_verification', title: 'Review / Verification', color: 'border-yellow-500/50' },
  { id: 'completed', title: 'Done', color: 'border-green-500/50' }
];

const WorkspaceBoard = ({ socket, onClose }) => {
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [fleetState, setFleetState] = useState({ agents: [], repos: [] });

  useEffect(() => {
    if (socket) {
      socket.emit('get_fleet_state');
      const handleFleetState = (data) => setFleetState(data);
      socket.on('fleet_state_update', handleFleetState);
      return () => socket.off('fleet_state_update', handleFleetState);
    }
  }, [socket]);

  // Auto-select first repo if none selected
  useEffect(() => {
    if (!selectedRepo && fleetState?.repos?.length > 0) {
      setSelectedRepo(fleetState.repos[0].name);
    }
  }, [fleetState, selectedRepo]);

  const handleDragStart = (e, taskId, sourceLane) => {
    e.dataTransfer.setData('taskId', taskId);
    e.dataTransfer.setData('sourceLane', sourceLane);
  };

  const handleDrop = (e, targetLane) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    const sourceLane = e.dataTransfer.getData('sourceLane');

    if (taskId && sourceLane !== targetLane && selectedRepo && socket) {
      socket.emit('update_task_status_lane', {
        repo_name: selectedRepo,
        task_id: taskId,
        status: targetLane
      });
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const repoData = fleetState?.repos?.find(r => r.name === selectedRepo);
  const tasks = repoData?.queue || [];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="fixed inset-0 z-[100] flex flex-col bg-black/90 backdrop-blur-xl text-gold9 font-mono overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gold9/20 bg-black/80" style={{ WebkitAppRegion: 'drag' }}>
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 bg-gold9/10 border border-gold9 rounded-lg flex items-center justify-center">
             <Layers className="w-5 h-5 text-gold9" />
          </div>
          <h1 className="text-2xl font-bold tracking-[0.2em] text-gold9 drop-shadow-[0_0_10px_rgba(255,215,0,0.5)] uppercase">
            Workspace Board
          </h1>
          <select
            className="bg-black/40 border border-gold9/30 text-gold9 rounded px-3 py-1 text-xs outline-none focus:border-gold9 transition-colors uppercase font-mono tracking-widest ml-4"
            value={selectedRepo || ''}
            onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ WebkitAppRegion: 'no-drag' }}
          >
            {fleetState?.repos?.map(r => (
              <option key={r.name} value={r.name}>{r.name}</option>
            ))}
          </select>
        </div>
        <button
          onClick={onClose}
          className="px-4 py-2 border border-gold9/30 hover:bg-gold9/10 hover:border-gold9 rounded text-xs tracking-widest transition-all"
          style={{ WebkitAppRegion: 'no-drag' }}
        >
          CLOSE BOARD
        </button>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 scrollbar-hide">
        <div className="flex space-x-6 h-full min-w-max">
          {LANE_CONFIG.map(lane => {
            const laneTasks = tasks.filter(t => t.status === lane.id || (lane.id === 'blocked' && t.status === 'blocked'));
            
            // Also map 'failed' to the lane it was in, but for now let's just group them by actual status
            return (
              <div
                key={lane.id}
                onDrop={(e) => handleDrop(e, lane.id)}
                onDragOver={handleDragOver}
                className={`flex flex-col w-80 bg-black/80 rounded-xl border border-gold9/20 border-t-4 ${lane.color} shadow-[0_0_15px_rgba(255,215,0,0.05)]`}
              >
                <div className="p-4 border-b border-gold9/10 flex justify-between items-center bg-gold9/5">
                  <h3 className="font-bold text-gold9 tracking-widest text-sm uppercase">{lane.title}</h3>
                  <span className="text-xs font-mono bg-gold9/20 text-gold9 px-2 py-1 rounded">
                    {laneTasks.length}
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
                  <AnimatePresence>
                    {laneTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        lane={lane.id}
                        onClick={() => setSelectedTask(task)}
                        onDragStart={(e) => handleDragStart(e, task.id, lane.id)}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Task Detail Panel Overlay */}
      <AnimatePresence>
        {selectedTask && (
          <TaskDetailPanel
            task={selectedTask}
            onClose={() => setSelectedTask(null)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const TaskCard = ({ task, lane, onClick, onDragStart }) => {
  const isBlocked = task.status === 'blocked' || task.status === 'failed';
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
      className={`p-3 rounded cursor-pointer border transition-all hover:-translate-y-0.5 group ${
        isBlocked 
          ? 'bg-red-500/10 border-red-500/30 hover:bg-red-500/20 hover:border-red-500/50 hover:shadow-[0_4px_15px_rgba(239,68,68,0.1)]' 
          : 'bg-gold9/5 border-gold9/10 hover:bg-gold9/20 hover:border-gold9/30 hover:shadow-[0_4px_15px_rgba(255,215,0,0.1)]'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] font-mono text-gold9/40 truncate w-2/3">ID: {task.id.substring(0, 8)}</span>
        {isBlocked && <AlertCircle className="w-3 h-3 text-red-400" />}
      </div>
      <p className="text-xs text-gold9 line-clamp-3 leading-relaxed mb-3">
        {task.prompt}
      </p>
      
      <div className="flex items-center justify-between text-[10px] text-gold9/40">
        <div className="flex items-center space-x-2">
          {task.agent_id ? (
            <span className="flex items-center space-x-1 bg-gold9/20 text-gold9 px-1.5 py-0.5 rounded border border-gold9/30">
              <Play className="w-2.5 h-2.5" />
              <span>{task.agent_id}</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1 opacity-50">
              <Clock className="w-2.5 h-2.5" />
              <span>UNASSIGNED</span>
            </span>
          )}
        </div>
        {task.attachments?.length > 0 && (
          <span className="flex items-center space-x-1">
            <FileText className="w-3 h-3" />
            <span>{task.attachments.length}</span>
          </span>
        )}
      </div>
    </motion.div>
  );
};

const TaskDetailPanel = ({ task, onClose }) => {
  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="absolute top-0 right-0 bottom-0 w-[500px] bg-[#111] border-l border-gold9/30 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] flex flex-col z-50 font-mono text-gold9"
    >
      <div className="p-4 border-b border-gold9/20 flex justify-between items-center bg-gold9/5">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
             <AlertCircle size={18} />
             TASK DETAILS
          </h2>
          <p className="text-[10px] text-gold9/40 mt-1">ID: {task.id}</p>
        </div>
        <button onClick={onClose} className="p-2 text-gold9/40 hover:text-gold9 transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
        <div>
          <h3 className="text-[10px] font-bold text-gold9/40 uppercase tracking-widest mb-2">STATUS</h3>
          <div className="inline-flex items-center space-x-2 bg-black/80 px-3 py-1.5 rounded border border-white/5">
            <div className={`w-2 h-2 rounded-full ${task.status === 'completed' ? 'bg-green-500' : task.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'}`} />
            <span className="text-xs text-gray-200 uppercase tracking-wider">{task.status.replace('_', ' ')}</span>
          </div>
        </div>

        <div>
          <h3 className="text-[10px] font-bold text-gold9/40 uppercase tracking-widest mb-2">PROMPT / DESCRIPTION</h3>
          <div className="bg-black/80 rounded p-4 text-xs text-gray-200 whitespace-pre-wrap border border-white/5 select-text">
            {task.prompt}
          </div>
        </div>

        {task.error_message && (
          <div>
            <h3 className="text-[10px] font-bold text-red-500/80 uppercase tracking-widest mb-2 flex items-center space-x-2">
              <AlertCircle className="w-3 h-3" />
              <span>FAILURE REASON</span>
            </h3>
            <div className="bg-red-500/20 border border-red-500/30 rounded p-4 text-xs text-red-400 whitespace-pre-wrap font-mono select-text">
              {task.error_message}
            </div>
          </div>
        )}

        {task.attachments?.length > 0 && (
          <div>
            <h3 className="text-[10px] font-bold text-gold9/40 uppercase tracking-widest mb-2">ATTACHMENTS ({task.attachments.length})</h3>
            <div className="space-y-2">
              {task.attachments.map((att, i) => (
                <div key={i} className="flex items-center space-x-3 bg-black/80 p-3 rounded border border-white/5">
                  <FileText className="w-4 h-4 text-gold9/60" />
                  <span className="text-xs text-gray-300">{att.name || `Attachment ${i + 1}`}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {task.session_id && (
          <div>
            <h3 className="text-[10px] font-bold text-gold9/40 uppercase tracking-widest mb-2">AGENT SESSION</h3>
            <div className="bg-black/80 rounded p-3 text-xs text-gray-300 border border-white/5 select-text">
              {task.session_id}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default WorkspaceBoard;
