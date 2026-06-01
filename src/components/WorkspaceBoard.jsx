import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Play, AlertCircle, FileText, CheckCircle, Clock } from 'lucide-react';

const LANE_CONFIG = [
  { id: 'backlog', title: 'Backlog', color: 'border-gray-600' },
  { id: 'todo_planning', title: 'Todo / Planning', color: 'border-blue-500' },
  { id: 'dev_implementation', title: 'Dev / Implementation', color: 'border-purple-500' },
  { id: 'review_verification', title: 'Review / Verification', color: 'border-yellow-500' },
  { id: 'completed', title: 'Done', color: 'border-green-500' }
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
      className="fixed inset-0 z-[100] flex flex-col bg-gray-900/95 backdrop-blur-xl text-white font-sans overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Workspace Board
          </h1>
          <select
            className="bg-gray-800 border border-gray-600 text-white rounded px-3 py-1 text-sm outline-none focus:border-blue-500 transition-colors"
            value={selectedRepo || ''}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            {fleetState?.repos?.map(r => (
              <option key={r.name} value={r.name}>{r.name}</option>
            ))}
          </select>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-red-500/20 text-gray-400 hover:text-red-400 rounded-full transition-colors"
        >
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6">
        <div className="flex space-x-6 h-full min-w-max">
          {LANE_CONFIG.map(lane => {
            const laneTasks = tasks.filter(t => t.status === lane.id || (lane.id === 'blocked' && t.status === 'blocked'));
            
            // Also map 'failed' to the lane it was in, but for now let's just group them by actual status
            return (
              <div
                key={lane.id}
                onDrop={(e) => handleDrop(e, lane.id)}
                onDragOver={handleDragOver}
                className={`flex flex-col w-80 bg-gray-800/40 rounded-xl border-t-4 ${lane.color} shadow-lg shadow-black/20`}
              >
                <div className="p-4 border-b border-gray-700/50 flex justify-between items-center">
                  <h3 className="font-semibold text-gray-200">{lane.title}</h3>
                  <span className="text-xs font-mono bg-gray-700 text-gray-300 px-2 py-1 rounded-full">
                    {laneTasks.length}
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
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
      className={`p-4 rounded-lg cursor-pointer border backdrop-blur-md transition-all hover:shadow-md ${
        isBlocked 
          ? 'bg-red-900/30 border-red-500/50 hover:bg-red-900/40 hover:border-red-400' 
          : 'bg-gray-700/40 border-gray-600/50 hover:bg-gray-700/60 hover:border-gray-500'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-mono text-gray-400 truncate w-2/3">{task.id}</span>
        {isBlocked && <AlertCircle className="w-4 h-4 text-red-400" />}
      </div>
      <p className="text-sm text-gray-200 line-clamp-3 leading-relaxed mb-3">
        {task.prompt}
      </p>
      
      <div className="flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center space-x-2">
          {task.agent_id ? (
            <span className="flex items-center space-x-1 bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded">
              <Play className="w-3 h-3" />
              <span>{task.agent_id}</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>Unassigned</span>
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
      className="absolute top-0 right-0 bottom-0 w-[500px] bg-gray-900/95 backdrop-blur-2xl border-l border-gray-700 shadow-2xl flex flex-col z-50"
    >
      <div className="p-6 border-b border-gray-700 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Task Details</h2>
          <p className="text-xs font-mono text-gray-400">{task.id}</p>
        </div>
        <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-full transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Status</h3>
          <div className="inline-flex items-center space-x-2 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700">
            <div className={`w-2 h-2 rounded-full ${task.status === 'completed' ? 'bg-green-500' : task.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'}`} />
            <span className="text-sm text-gray-200 capitalize">{task.status.replace('_', ' ')}</span>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Prompt / Description</h3>
          <div className="bg-gray-800/50 rounded-lg p-4 text-sm text-gray-300 whitespace-pre-wrap border border-gray-700/50">
            {task.prompt}
          </div>
        </div>

        {task.error_message && (
          <div>
            <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-2 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4" />
              <span>Blocker / Error Analysis</span>
            </h3>
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 text-sm text-red-200 whitespace-pre-wrap">
              {task.error_message}
            </div>
          </div>
        )}

        {task.attachments?.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Attachments ({task.attachments.length})</h3>
            <div className="space-y-2">
              {task.attachments.map((att, i) => (
                <div key={i} className="flex items-center space-x-3 bg-gray-800 p-3 rounded-lg border border-gray-700">
                  <FileText className="w-5 h-5 text-gray-400" />
                  <span className="text-sm text-gray-300">{att.name || `Attachment ${i + 1}`}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {task.session_id && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Agent Session</h3>
            <div className="bg-gray-800/50 rounded-lg p-3 text-sm text-gray-300 font-mono border border-gray-700/50">
              {task.session_id}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default WorkspaceBoard;
