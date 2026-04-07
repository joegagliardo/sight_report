document.addEventListener('DOMContentLoaded', () => {
    const timeline = document.getElementById('prompt-timeline');
    const editor = document.getElementById('prompt-content');
    const saveBtn = document.getElementById('save-btn');
    const versionCount = document.getElementById('version-count');
    const saveStatus = document.getElementById('save-status');
    const agentList = document.getElementById('agent-list');

    let allPrompts = [];
    let currentAgent = ''; 
    let selectedPromptId = null;

    const fetchPrompts = async () => {
        try {
            const response = await fetch('/api/prompts');
            const data = await response.json();
            allPrompts = data.prompts || [];
            
            // Extract unique agents
            const uniqueAgents = [...new Set(allPrompts.map(p => p.agent_name))];
            
            // Set default agent if none selected
            if (!currentAgent && uniqueAgents.length > 0) {
                currentAgent = uniqueAgents[0];
            }
            
            renderAgentList(uniqueAgents);
            renderTimeline();
        } catch (error) {
            console.error('Error fetching prompts:', error);
            timeline.innerHTML = '<div style="padding: 2rem; color: #991b1b;">Failed to load history. Check Firestore connection.</div>';
        }
    };

    const renderAgentList = (agents) => {
        agentList.innerHTML = '';
        agents.forEach(agent => {
            const item = document.createElement('div');
            item.className = `history-item ${agent === currentAgent ? 'active' : ''}`;
            item.innerText = agent;
            item.style.marginBottom = '4px';
            
            item.onclick = () => {
                currentAgent = agent;
                document.querySelectorAll('#agent-list .history-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                
                // Reset editor before rendering timeline
                editor.value = '';
                renderTimeline();
            };
            
            agentList.appendChild(item);
        });
    };

    const renderTimeline = () => {
        timeline.innerHTML = '';
        const agentPrompts = allPrompts.filter(p => p.agent_name === currentAgent);
        versionCount.innerText = `${agentPrompts.length} Versions`;

        if (agentPrompts.length === 0) {
            timeline.innerHTML = `<div style="padding: 2rem; text-align: center; color: var(--text-secondary);">No history for agent "${currentAgent}"</div>`;
            editor.value = '';
            document.getElementById('editor-title').innerText = 'New Prompt Definition';
            return;
        }

        agentPrompts.forEach((prompt, index) => {
            const date = new Date(prompt.date_entered || Date.now());
            const dateStr = date.toLocaleString();
            const isLatest = index === 0;

            const item = document.createElement('div');
            item.className = `prompt-item ${isLatest ? 'active' : ''}`;
            item.innerHTML = `
                <div class="prompt-date">${dateStr}</div>
                <div class="prompt-version-label">
                    Version ${agentPrompts.length - index}
                    ${isLatest ? '<span class="badge latest" style="margin-left: 8px;">ACTIVE</span>' : ''}
                </div>
            `;

            item.onclick = () => {
                // Remove active from any other item
                document.querySelectorAll('.prompt-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                
                // Show in editor
                editor.value = prompt.instructions;
                
                // If not latest, let user know they can only append
                if (!isLatest) {
                    saveBtn.innerText = 'Restore as New Version';
                    document.getElementById('editor-title').innerText = `Viewing Historical Version (${dateStr})`;
                } else {
                    saveBtn.innerHTML = `
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v13a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                        Save New Version
                    `;
                    document.getElementById('editor-title').innerText = 'Current Active Definition';
                }
            };

            timeline.appendChild(item);

            // Load the latest into editor by default on first run or agent change
            if (isLatest && !editor.value) {
                editor.value = prompt.instructions;
                document.getElementById('editor-title').innerText = 'Current Active Definition';
            }
        });
    };

    const showStatus = (msg, type) => {
        saveStatus.innerHTML = `<span class="${type}-text">${msg}</span>`;
        saveStatus.style.opacity = '1';
        setTimeout(() => {
            saveStatus.style.opacity = '0';
        }, 3000);
    };

    saveBtn.onclick = async () => {
        const instructions = editor.value.trim();
        if (!instructions) return;

        const originalBtnContent = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerText = 'Saving...';

        try {
            const response = await fetch('/api/prompts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_name: currentAgent,
                    instructions: instructions
                })
            });

            if (response.ok) {
                saveBtn.innerText = 'Saved';
                showStatus('✅ New version saved successfully!', 'success');
                await fetchPrompts(); // Refresh timeline and data
                
                setTimeout(() => {
                    saveBtn.innerHTML = originalBtnContent;
                    saveBtn.disabled = false;
                }, 2000);
            } else {
                throw new Error('Failed to save');
            }
        } catch (error) {
            showStatus('❌ Failed to save. Check server logs.', 'error');
            saveBtn.innerHTML = originalBtnContent;
            saveBtn.disabled = false;
        }
    };

    // Initial fetch
    fetchPrompts();
});
