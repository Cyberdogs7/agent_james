def patch():
    with open("src/components/WarRoomDashboard.jsx", "r") as f:
        content = f.read()

    target = "onClearCompleted={(repoName) => socket.emit('clear_completed_tasks', { repo_name: repoName })}"
    replacement = target + "\n                            onToggleRepoActive={(repoName, isActive) => socket.emit('set_repo_active_state', { repo_name: repoName, is_active: isActive })}"

    if "onToggleRepoActive" not in content:
        content = content.replace(target, replacement)

    with open("src/components/WarRoomDashboard.jsx", "w") as f:
        f.write(content)

patch()
