import React, { useState, useEffect } from 'react';
import { X, Folder, Plus, Check } from 'lucide-react';

const ProjectWindow = ({
    socket,
    position,
    onClose,
    activeDragElement,
    onMouseDown,
    zIndex = 50,
    currentProject
}) => {
    const [projects, setProjects] = useState([]);
    const [newProjectName, setNewProjectName] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    useEffect(() => {
        // Initial fetch
        socket.emit('list_projects');

        const onProjectList = (list) => {
            console.log("Projects loaded:", list);
            setProjects(list || []);
        };

        const onProjectUpdate = (data) => {
            // Refresh list when a project updates/is created
            socket.emit('list_projects');
        };

        socket.on('project_list', onProjectList);
        socket.on('project_update', onProjectUpdate);

        return () => {
            socket.off('project_list', onProjectList);
            socket.off('project_update', onProjectUpdate);
        };
    }, [socket]);

    const handleSwitch = (name) => {
        if (name === currentProject) return;
        socket.emit('switch_project', { project_name: name });
    };

    const handleCreate = () => {
        if (!newProjectName.trim()) return;
        setIsCreating(true);
        socket.emit('create_project', { project_name: newProjectName });

        // Reset creating state after a delay or on update (using timeout for simplicity)
        setTimeout(() => setIsCreating(false), 2000);
        setNewProjectName('');
    };

    return (
        <div
            id="project_window"
            onMouseDown={onMouseDown}
            className={`absolute flex flex-col gap-2 p-4 rounded-xl  bg-black/80 border border-gold9/20 ${activeDragElement === "project_window" ? "" : "transition-[left,top] duration-200"} select-none
                ${activeDragElement === 'project_window' ? 'ring-2 ring-green-500 shadow-[0_0_30px_rgba(34,197,94,0.3)]' : 'shadow-[0_0_20px_rgba(255,215,0,0.1)]'}
            `}
            style={{
                left: position.x,
                top: position.y,
                width: '300px',
                minHeight: '300px',
                transform: 'translate(-50%, -50%)',
                zIndex: zIndex
            }}
        >
            {/* Header */}
            <div data-drag-handle className="flex items-center justify-between pb-2 border-b border-white/10 mb-2 cursor-grab active:cursor-grabbing">
                <div className="flex items-center gap-2">
                    <Folder size={16} className="text-gold9" />
                    <h3 className="font-bold text-gold9 tracking-wider text-sm">PROJECTS</h3>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-white"
                >
                    <X size={16} />
                </button>
            </div>

            {/* Create New */}
            <div className="flex gap-2 mb-4">
                <input
                    type="text"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    placeholder="New Project Name..."
                    className="flex-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-sm text-white focus:border-gold9/50 outline-none"
                    onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
                <button
                    onClick={handleCreate}
                    disabled={isCreating}
                    className="p-1.5 bg-gold9/10 hover:bg-gold9/20 border border-gold9/20 rounded text-gold9 transition-colors"
                >
                    {isCreating ? <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" /> : <Plus size={16} />}
                </button>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto max-h-[300px] scrollbar-hide flex flex-col gap-1">
                {projects.map((proj) => (
                    <button
                        key={proj}
                        onClick={() => handleSwitch(proj)}
                        className={`group flex items-center justify-between p-2 rounded text-left transition-all border ${
                            proj === currentProject
                            ? 'bg-gold9/20 border-gold9/50 text-gold9'
                            : 'bg-transparent border-transparent hover:bg-white/5 text-gray-300 hover:text-white'
                        }`}
                    >
                        <span className="text-sm font-medium truncate">{proj}</span>
                        {proj === currentProject && <Check size={14} className="text-gold9" />}
                    </button>
                ))}
                {projects.length === 0 && (
                    <div className="text-center text-xs text-white/30 py-4">No projects found</div>
                )}
            </div>
        </div>
    );
};

export default ProjectWindow;
