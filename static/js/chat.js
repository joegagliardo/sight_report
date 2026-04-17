document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');

    let sessionId = 'session_' + Math.random().toString(36).substring(7);

    // New Chat handler
    newChatBtn.addEventListener('click', () => {
        sessionId = 'session_' + Math.random().toString(36).substring(7);
        chatMessages.innerHTML = `
            <div class="message agent animate-entry">
                <div class="message-content">
                    Hello! I'm your Sight Report Analyst. Provide a company name, and I'll fetch the pipeline data, analyze content gaps, and suggest followup GCP courses.
                </div>
            </div>
        `;
        userInput.value = '';
        userInput.style.height = 'auto';
    });

    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = (userInput.scrollHeight) + 'px';
    });

    const appendMessage = (text, type) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type} animate-entry`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerText = text;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return contentDiv;
    };

    // --- PDF Generation Logic ---
    const generatePDF = (element, companyName = 'Sight_Report') => {
        const opt = {
            margin: 0.75,
            filename: `Sight_Report_${companyName}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
        };
        
        // Prepare a clean version for the PDF
        const pdfContainer = document.createElement('div');
        pdfContainer.style.padding = '20px';
        pdfContainer.style.color = '#000';
        pdfContainer.style.fontFamily = 'Arial, sans-serif';
        pdfContainer.style.lineHeight = '1.6';

        const header = document.createElement('div');
        header.innerHTML = `
            <h1 style="color: #1d4ed8; border-bottom: 2px solid #1d4ed8; padding-bottom: 10px; margin-bottom: 20px;">
                S.I.G.H.T. Analysis Report
            </h1>
            <p style="color: #666; margin-bottom: 30px;"><strong>Client:</strong> ${companyName} | <strong>Generated:</strong> ${new Date().toLocaleDateString()}</p>
        `;
        
        const bodyContent = document.createElement('div');
        bodyContent.innerHTML = element.innerHTML;
        
        pdfContainer.appendChild(header);
        pdfContainer.appendChild(bodyContent);

        html2pdf().from(pdfContainer).set(opt).save();
    };

    const showDownloadButton = (parentDiv, companyName) => {
        const btn = document.createElement('button');
        btn.className = 'download-btn';
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Download Report PDF
        `;
        btn.onclick = () => generatePDF(parentDiv, companyName);
        parentDiv.parentElement.appendChild(btn);
    };

    const formatText = (text) => {
        return text
            .replace(/\[\[INFOGRAPHIC:(.*?)\]\]/g, (match, path) => {
                const cleanPath = path.trim();
                return `<div class="generated-image-container">
                    <img src="/${cleanPath}" class="generated-image" alt="Infographic" loading="lazy">
                </div>`;
            })
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\[(.*?)\]\((.*?)\)/g, (match, title, url) => {
                let finalUrl = url.trim();
                // Client-side fallback for GCS paths
                if (finalUrl.startsWith('gs://')) {
                    finalUrl = finalUrl.replace('gs://', 'https://storage.googleapis.com/');
                }
                return `<a href="${finalUrl}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue); text-decoration: underline;">${title}</a>`;
            })
            // Auto-link plain URLs that aren't already part of a markdown link
            .replace(/(?<!href=")(?<!">)(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue); text-decoration: underline;">$1</a>')
            .replace(/^- (.*)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/gms, '<ul>$1</ul>')
            .replace(/\n/g, '<br>');
    };

    const streamResponse = async (prompt) => {
        appendMessage(prompt, 'user');
        
        const companyMatch = prompt.match(/\b([A-Z][a-z0-9]+)\b/);
        const companyName = companyMatch ? companyMatch[1] : 'Analysis';

        userInput.value = '';
        userInput.style.height = 'auto';
        
        // Detect Agent
        let agent_name = 'sight_reader';
        if (prompt.toLowerCase().includes('logo') || prompt.toLowerCase().includes('generate') || prompt.toLowerCase().includes('image')) {
            agent_name = 'sight_logo';
        }

        const agentContentDiv = appendMessage('', 'agent');
        agentContentDiv.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, sessionId, agent_name })
            });

            if (!response.ok) throw new Error('Failed to connect to agent');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            let isFirstChunk = true;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                console.log('--- RAW CHUNK RECEIVED ---', chunk);
                
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.replace('data: ', '');
                        
                        if (data === '[PULSE]' || !data.trim()) {
                            continue;
                        }

                        if (isFirstChunk) {
                            agentContentDiv.innerHTML = '';
                            isFirstChunk = false;
                        }
                        
                        if (data.startsWith('MEDIA:')) {
                            const mediaUrl = data.replace('MEDIA:', '');
                            agentContentDiv.innerHTML += `<div class="generated-image-container">
                                <img src="${mediaUrl}" class="generated-image" alt="Generated Logo" loading="lazy">
                            </div>`;
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                            continue;
                        }

                        fullText += data + '\n';
                        agentContentDiv.innerHTML = formatText(fullText);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                }
            }
            
            // if (!isFirstChunk) {
            //     showDownloadButton(agentContentDiv, companyName);
            // }

        } catch (error) {
            agentContentDiv.innerText = 'Error: ' + error.message;
            agentContentDiv.classList.add('error');
        }
    };

    const handleSend = () => {
        const text = userInput.value.trim();
        if (text) streamResponse(text);
    };

    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
});
