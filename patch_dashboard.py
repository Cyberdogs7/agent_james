import re

with open("src/components/WarRoomDashboard.jsx", "r") as f:
    content = f.read()

# Add imports
imports = """import PlanVisualizer from './PlanVisualizer';
import AutomationEditor from './AutomationEditor';
import SwarmVisualizer from './SwarmVisualizer';
import FleetManagerUI from './FleetManagerUI';
"""
content = content.replace("import SwarmVisualizer from './SwarmVisualizer';", imports)

# Add state
state_code = """    const [viewMode, setViewMode] = useState('spatial'); // 'spatial' or 'list'
    const [fleetState, setFleetState] = useState({ agents: [], repos: [] });

    // Add effect for fleet state
    useEffect(() => {
        if (socket) {
            socket.emit('get_fleet_state');
            const handleFleetState = (data) => setFleetState(data);
            socket.on('fleet_state_update', handleFleetState);
            return () => socket.off('fleet_state_update', handleFleetState);
        }
    }, [socket]);
"""
content = content.replace("    const [viewMode, setViewMode] = useState('spatial'); // 'spatial' or 'list'", state_code)

# Add Tab
tab_code = """                    <button
                        onClick={() => setActiveTab('fleet')}
                        className={`px-4 py-2 text-xs font-bold tracking-widest uppercase transition-colors ${activeTab === 'fleet' ? 'text-gold9 border-b-2 border-gold9' : 'text-gold9/40 hover:text-gold9/80'}`}
                    >
                        Fleet Manager
                    </button>
                    <button
                        onClick={() => setActiveTab('trello')}"""
content = content.replace("<button \n                        onClick={() => setActiveTab('trello')}", tab_code)

# Add Render Logic
render_code = """
                        {activeTab === 'fleet' && (
                            <FleetManagerUI
                                fleetState={fleetState}
                                onAssign={(agentId, repoName) => socket && socket.emit('assign_agent_to_repo', { agent_id: agentId, repo_name: repoName })}
                                onUnassign={(agentId) => socket && socket.emit('unassign_agent', { agent_id: agentId })}
                                onAddTask={(repoName, prompt) => socket && socket.emit('add_task_to_repo_queue', { repo_name: repoName, prompt })}
                                onRemoveTask={(repoName, taskId) => socket && socket.emit('remove_task_from_queue', { repo_name: repoName, task_id: taskId })}
                            />
                        )}
                        {activeTab === 'trello' && ("""
content = content.replace("{activeTab === 'trello' && (", render_code)

with open("src/components/WarRoomDashboard.jsx", "w") as f:
    f.write(content)
