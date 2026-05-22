document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Views
    const setupView = document.getElementById('setup-view');
    const interviewView = document.getElementById('interview-view');
    const scorecardView = document.getElementById('scorecard-view');
    
    const setupForm = document.getElementById('setup-form');
    const submitBtn = document.getElementById('submit-answer-btn');
    const chatOutput = document.getElementById('chat-output');
    const micText = document.getElementById('mic-text');
    const micDot = document.getElementById('mic-dot');
    const restartBtn = document.getElementById('restart-btn');
    
    let qaPairs = [];
    let turnCount = 0;
    const MAX_TURNS = 3;
    let isInterviewActive = false;
    let icpProfile = {};
    
    let currentUtterance = null;
    let currentTranscript = "";
    let activeQuestion = "";

    // Web Speech
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
    } else {
        alert('Web Speech API is not supported in this browser. Please use Chrome or Edge.');
        document.getElementById('start-demo-btn').disabled = true;
    }

    // Pre-load voices for Chrome bug
    let availableVoices = [];
    function loadVoices() {
        if(window.speechSynthesis) availableVoices = window.speechSynthesis.getVoices();
    }
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
        loadVoices();
    }

    function setMicStatus(status) {
        if (status === 'listening') {
            micText.innerText = 'Listening...';
            micText.style.color = '#ef4444';
            micDot.style.backgroundColor = '#ef4444';
            submitBtn.style.display = 'inline-block';
        } else if (status === 'speaking') {
            micText.innerText = 'AI Speaking...';
            micText.style.color = '#3b82f6';
            micDot.style.backgroundColor = '#3b82f6';
            submitBtn.style.display = 'none';
        } else if (status === 'processing') {
            micText.innerText = 'Processing...';
            micText.style.color = '#f59e0b';
            micDot.style.backgroundColor = '#f59e0b';
            submitBtn.style.display = 'none';
        } else {
            micText.innerText = 'Inactive';
            micText.style.color = '#64748b';
            micDot.style.backgroundColor = '#64748b';
            submitBtn.style.display = 'none';
        }
    }

    function addChatBubble(sender, text) {
        const msgElem = document.createElement('div');
        msgElem.className = `chat-message ${sender}`;
        
        const safeText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const label = sender === 'ai' ? 'Conductor' : (sender === 'user' ? 'You' : 'System');
        
        if (sender === 'system-message') {
            msgElem.innerHTML = `<span>${safeText}</span>`;
        } else {
            msgElem.innerHTML = `
                <div class="sender-label">${label}</div>
                <div class="bubble">${safeText}</div>
            `;
        }
        
        chatOutput.appendChild(msgElem);
        chatOutput.scrollTop = chatOutput.scrollHeight;
        return msgElem;
    }

    function speakText(text, callback) {
        if (!window.speechSynthesis) {
            if(callback) callback();
            return;
        }
        setMicStatus('speaking');
        currentUtterance = new SpeechSynthesisUtterance(text);
        
        const targetLangCode = (icpProfile && icpProfile.language === 'hi') ? 'hi' : 'en';
        currentUtterance.lang = targetLangCode === 'hi' ? 'hi-IN' : 'en-US';
        
        let preferredVoice = availableVoices.find(v => v.lang.includes(targetLangCode) && (v.name.includes('Google') || v.name.includes('Natural')));
        if (!preferredVoice) {
            preferredVoice = availableVoices.find(v => v.lang.includes(targetLangCode)) || availableVoices[0];
        }
        
        if (preferredVoice) currentUtterance.voice = preferredVoice;

        currentUtterance.onend = () => {
            setMicStatus('inactive');
            if (callback) callback();
        };
        currentUtterance.onerror = () => {
            setMicStatus('inactive');
            if (callback) callback();
        }
        window.speechSynthesis.speak(currentUtterance);
    }

    async function fetchNextQuestion() {
        setMicStatus('processing');
        try {
            const res = await fetch('/api/conduct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    previous_qa_pairs: qaPairs,
                    icp_profile: icpProfile
                })
            });
            const data = await res.json();
            
            const nextQ = data.next_question;
            addChatBubble('ai', nextQ);
            
            speakText(nextQ, () => {
                startListening(nextQ);
            });
        } catch (err) {
            addChatBubble('system-message', `Error connecting to backend: ${err.message}`);
            resetInterview();
        }
    }

    let activeUserBubble = null;

    function startListening(question) {
        if (!recognition) return;
        activeQuestion = question;
        currentTranscript = "";
        
        const msgElem = addChatBubble('user', '');
        activeUserBubble = msgElem.querySelector('.bubble');
        
        setMicStatus('listening');
        
        recognition.onresult = (event) => {
            let finalText = '';
            let interimText = '';

            for (let i = 0; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalText += event.results[i][0].transcript;
                } else {
                    interimText += event.results[i][0].transcript;
                }
            }
            
            currentTranscript = finalText;
            
            if (activeUserBubble) {
                activeUserBubble.innerText = finalText + interimText;
            }
        };

        recognition.onerror = (event) => {
            if (event.error !== 'no-speech') {
                addChatBubble('system-message', `Speech error: ${event.error}`);
            }
        };

        recognition.onend = () => {
            setMicStatus('inactive');
        };

        try { recognition.start(); } catch(e) {}
    }
    
    submitBtn.addEventListener('click', () => {
        if (recognition) recognition.stop();
        
        if (!currentTranscript && activeUserBubble) {
             currentTranscript = activeUserBubble.innerText;
        }
        
        if (!currentTranscript.trim()) {
            addChatBubble('system-message', 'No answer recorded. Please answer again.');
            startListening(activeQuestion);
            return;
        }

        qaPairs.push({
            question: activeQuestion,
            answer_transcript: currentTranscript.trim()
        });
        
        turnCount++;
        if (turnCount < MAX_TURNS) {
            fetchNextQuestion();
        } else {
            finishInterview();
        }
    });

    async function finishInterview() {
        setMicStatus('processing');
        addChatBubble('system-message', 'Interview complete! Generating your visual score report...');
        
        const transcriptForScorer = qaPairs.map(p => ({
            question: p.question,
            answer: p.answer_transcript
        }));

        try {
            const res = await fetch('/api/score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    full_transcript: transcriptForScorer,
                    icp_profile: icpProfile
                })
            });
            const data = await res.json();
            
            renderScorecard(data);
            
            speakText(`Interview complete. Your overall score is ${data.overall_score} out of 100.`, () => {
                resetInterview();
                interviewView.style.display = 'none';
                scorecardView.style.display = 'flex';
            });

        } catch (err) {
            addChatBubble('system-message', `Error fetching score: ${err.message}`);
            resetInterview();
        }
    }

    function renderScorecard(data) {
        // Animate Overall Score Circle
        const scoreCircle = document.querySelector('.score-circle');
        const scoreValElem = document.getElementById('overall-score-val');
        
        let currentScore = 0;
        const targetScore = data.overall_score || 0;
        const duration = 1500; 
        const interval = 20;
        const steps = duration / interval;
        const increment = targetScore / steps;
        
        const scoreTimer = setInterval(() => {
            currentScore += increment;
            if (currentScore >= targetScore) {
                currentScore = targetScore;
                clearInterval(scoreTimer);
            }
            scoreValElem.innerText = Math.round(currentScore);
            scoreCircle.style.background = `conic-gradient(var(--primary) ${currentScore * 3.6}deg, rgba(255,255,255,0.05) 0deg)`;
        }, interval);
        
        const axesContainer = document.getElementById('axes-container');
        axesContainer.innerHTML = '';
        
        if (data.scores_per_axis) {
            Object.keys(data.scores_per_axis).forEach(axis => {
                const score = data.scores_per_axis[axis];
                const gap = data.gap_vs_bar ? data.gap_vs_bar[axis] : 0;
                const isGood = gap >= 0;
                
                const axisHtml = `
                    <div class="axis-row">
                        <div class="axis-header">
                            <span class="axis-name">${axis.replace('_', ' ')}</span>
                            <span class="axis-score" style="color: ${isGood ? 'var(--success)' : 'var(--danger)'}">${score}/100</span>
                        </div>
                        <div class="progress-bg">
                            <div class="progress-bar ${isGood ? 'good' : 'bad'}" style="width: 0%" data-target="${score}%"></div>
                        </div>
                    </div>
                `;
                axesContainer.innerHTML += axisHtml;
            });
            
            // Trigger progress bar slide-in animation
            setTimeout(() => {
                document.querySelectorAll('.progress-bar').forEach(bar => {
                    bar.style.width = bar.getAttribute('data-target');
                });
            }, 100);
        }
        
        if (data.strong_moment) {
            document.getElementById('strong-quote').innerText = `"${data.strong_moment.quote}"`;
            document.getElementById('strong-reason').innerText = data.strong_moment.why_it_helped;
            document.getElementById('strong-quote').parentElement.style.display = 'block';
        } else {
            document.getElementById('strong-quote').parentElement.style.display = 'none';
        }
        
        if (data.weak_moment) {
            document.getElementById('weak-quote').innerText = `"${data.weak_moment.quote}"`;
            document.getElementById('weak-reason').innerText = data.weak_moment.why_it_hurt;
            document.getElementById('weak-quote').parentElement.style.display = 'block';
        } else {
            document.getElementById('weak-quote').parentElement.style.display = 'none';
        }
        
        if (data.next_action) {
            document.getElementById('next-action').innerText = data.next_action;
            document.getElementById('next-action').parentElement.style.display = 'block';
        } else {
            document.getElementById('next-action').parentElement.style.display = 'none';
        }
    }

    function resetInterview() {
        isInterviewActive = false;
        setMicStatus('inactive');
        if(recognition) recognition.stop();
    }

    // Sync profile cards with customizable form inputs
    const profileRadios = document.querySelectorAll('input[name="profile_choice"]');
    const targetRoleInput = document.getElementById('target-role');
    const roundTypeSelect = document.getElementById('round-type');
    const companyTierSelect = document.getElementById('company-tier');

    profileRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'user_a') {
                targetRoleInput.value = 'Software Engineering';
                roundTypeSelect.value = 'technical';
                companyTierSelect.value = 'enterprise';
            } else {
                targetRoleInput.value = 'Customer Support / Delivery';
                roundTypeSelect.value = 'behavioral';
                companyTierSelect.value = 'startup';
            }
        });
    });

    setupForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const selectedProfile = document.querySelector('input[name="profile_choice"]:checked').value;
        
        icpProfile = {
            target_role: targetRoleInput.value,
            round_type: roundTypeSelect.value,
            company_tier: companyTierSelect.value,
            icp_type: selectedProfile === 'user_a' ? 'high_wage' : 'low_wage',
            language: selectedProfile === 'user_a' ? 'en' : 'hi'
        };

        if(recognition) {
            recognition.lang = selectedProfile === 'user_a' ? 'en-IN' : 'hi-IN';
        }

        setupView.style.display = 'none';
        interviewView.style.display = 'flex';
        
        isInterviewActive = true;
        chatOutput.innerHTML = '';
        qaPairs = [];
        turnCount = 0;
        
        addChatBubble('system-message', 'Interview Session Initialized.');
        fetchNextQuestion();
    });

    restartBtn.addEventListener('click', () => {
        scorecardView.style.display = 'none';
        setupView.style.display = 'flex';
    });
});
