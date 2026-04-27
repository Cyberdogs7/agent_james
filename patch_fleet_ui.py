def patch():
    with open("src/components/FleetManagerUI.jsx", "r") as f:
        content = f.read()

    # Update props
    if "onToggleRepoActive" not in content.split("\n")[4]:
        content = content.replace(
            "const FleetManagerUI = ({ fleetState, fleetStatus = [], julesSessions = [], onAssign, onUnassign, onAddTask, onRemoveTask, onClearCompleted }) => {",
            "const FleetManagerUI = ({ fleetState, fleetStatus = [], julesSessions = [], onAssign, onUnassign, onAddTask, onRemoveTask, onClearCompleted, onToggleRepoActive }) => {"
        )

    # Initialize is_active state
    all_repos_map_logic = """    fleetStatus.forEach(repo => {
        allReposMap.set(repo.name, { ...repo, queue: [], is_active: false });
    });
    stateRepos.forEach(repo => {
        if (allReposMap.has(repo.name)) {
            allReposMap.get(repo.name).queue = repo.queue || [];
            allReposMap.get(repo.name).is_active = repo.is_active || false;
        } else {
            allReposMap.set(repo.name, { name: repo.name, queue: repo.queue || [], is_active: repo.is_active || false });
        }
    });"""

    old_all_repos_map_logic = """    fleetStatus.forEach(repo => {
        allReposMap.set(repo.name, { ...repo, queue: [] });
    });
    stateRepos.forEach(repo => {
        if (allReposMap.has(repo.name)) {
            allReposMap.get(repo.name).queue = repo.queue || [];
        } else {
            allReposMap.set(repo.name, { name: repo.name, queue: repo.queue || [] });
        }
    });"""

    if "is_active" not in content.split("const repos =")[0]:
        content = content.replace(old_all_repos_map_logic, all_repos_map_logic)

    # Split repos
    repo_split_logic = """    const repos = Array.from(allReposMap.values());
    const activeRepos = repos.filter(r => r.is_active);
    const inactiveRepos = repos.filter(r => !r.is_active);"""

    if "activeRepos =" not in content:
        content = content.replace("    const repos = Array.from(allReposMap.values());", repo_split_logic)

    # Sidebar: add inactive repos
    sidebar_target = """                <div className="flex-1 overflow-y-auto p-4 scrollbar-hide">
                    <div className="text-xs font-bold text-gold9/40 mb-3 tracking-widest">UNASSIGNED</div>"""

    sidebar_replacement = """                <div className="flex-1 overflow-y-auto p-4 scrollbar-hide">
                    <div className="text-xs font-bold text-gold9/40 mb-3 tracking-widest">AVAILABLE REPOS</div>
                    {inactiveRepos.map(repo => (
                        <div key={repo.name} className="flex items-center justify-between p-2 mb-2 rounded bg-black/40 border border-gold9/20 hover:border-gold9 transition-colors">
                            <span className="text-sm font-mono text-gray-100 truncate flex-1" title={repo.name}>{repo.name}</span>
                            <button onClick={() => onToggleRepoActive && onToggleRepoActive(repo.name, true)} className="text-gold9/60 hover:text-gold9 ml-2 p-1">
                                <Plus size={14} />
                            </button>
                        </div>
                    ))}
                    {inactiveRepos.length === 0 && (
                        <div className="text-center text-sm text-gold9/40 py-4 font-mono italic">
                            No inactive repos.
                        </div>
                    )}

                    <div className="text-xs font-bold text-gold9/40 mt-6 mb-3 tracking-widest">UNASSIGNED AGENTS</div>"""

    if "AVAILABLE REPOS" not in content:
        content = content.replace(sidebar_target, sidebar_replacement)

    # Main Area: use activeRepos and add move out button
    main_target = "{repos.map(repo => {"
    main_replacement = "{activeRepos.map(repo => {"
    if main_target in content:
        content = content.replace(main_target, main_replacement)

    header_target = """                                    <h3 className="font-bold text-gold9 font-mono flex items-center gap-2">
                                        <Server size={16} />
                                        {repo.name}
                                    </h3>
                                    <div className="text-xs text-gold9/60 font-mono">
                                        {repoAgents.length} AGENTS
                                    </div>"""

    header_replacement = """                                    <h3 className="font-bold text-gold9 font-mono flex items-center gap-2">
                                        <Server size={16} />
                                        <span className="truncate max-w-[200px]" title={repo.name}>{repo.name}</span>
                                    </h3>
                                    <div className="flex items-center gap-3">
                                        <div className="text-xs text-gold9/60 font-mono">
                                            {repoAgents.length} AGENTS
                                        </div>
                                        <button onClick={() => onToggleRepoActive && onToggleRepoActive(repo.name, false)} className="text-gold9/40 hover:text-red-500 transition-colors p-1" title="Deactivate Repo">
                                            <X size={14} />
                                        </button>
                                    </div>"""

    if "Deactivate Repo" not in content:
        content = content.replace(header_target, header_replacement)

    # Need to make sure we import X from lucide-react in FleetManagerUI.jsx
    import_target = "import { Layers, Activity, AlertTriangle, Plus, ChevronRight, Server, Play, Clock, Inbox } from 'lucide-react';"
    import_replacement = "import { Layers, Activity, AlertTriangle, Plus, ChevronRight, Server, Play, Clock, Inbox, X } from 'lucide-react';"
    if "import { Layers, Activity, AlertTriangle, Plus, ChevronRight, Server, Play, Clock, Inbox, X } from 'lucide-react';" not in content:
        content = content.replace(import_target, import_replacement)

    with open("src/components/FleetManagerUI.jsx", "w") as f:
        f.write(content)

patch()
