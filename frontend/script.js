document.addEventListener('DOMContentLoaded', () => {
    const tabBtns = document.querySelectorAll('.tab-switcher .tab-btn');
    const forms = document.querySelectorAll('.input-form');
    
    // Right Pane containers
    const placeholderState = document.getElementById('placeholder-state');
    const singleResultsContainer = document.getElementById('single-results-container');
    const batchProgressContainer = document.getElementById('batch-progress-container');

    let sgpaChartInstance = null; // Store chart instance to destroy before re-rendering

    // Switch Right Pane view
    function setRightPaneView(viewId) {
        placeholderState.style.display = 'none';
        singleResultsContainer.style.display = 'none';
        batchProgressContainer.style.display = 'none';
        
        if (viewId === 'placeholder') placeholderState.style.display = 'flex';
        else if (viewId === 'single') singleResultsContainer.style.display = 'block';
        else if (viewId === 'batch') batchProgressContainer.style.display = 'flex';
    }

    // Tab Switching Logic
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            forms.forEach(f => f.classList.remove('active-form'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active-form');
            
            // If Exports tab clicked, fetch the list
            if (targetId === 'exports-panel') {
                fetchExports();
            }
        });
    });

    // Session Calculation Logic
    function generateSessionsList(rollNo) {
        if (!rollNo || rollNo.length < 2) return [];
        const admYearShort = parseInt(rollNo.substring(0, 2));
        if (isNaN(admYearShort)) return [];
        const admYear = 2000 + admYearShort;
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1; 
        
        let sessions = [];
        for (let y = admYear; y <= currentYear; y++) {
            const nextY = (y + 1).toString().substring(2);
            const ayStr = `${y}-${nextY}`;
            sessions.push(`Odd-(${ayStr})`);
            sessions.push(`Even-(${ayStr})`);
        }
        
        const sessionType = currentMonth >= 6 ? "Even" : "Odd";
        const currentAyStr = `${currentYear - 1}-${currentYear.toString().substring(2)}`;
        const currentSession = `${sessionType}-(${currentAyStr})`;
        
        const idx = sessions.indexOf(currentSession);
        if (idx !== -1) {
            sessions = sessions.slice(0, idx + 1);
        }
        
        return sessions.reverse();
    }

    function updateSessionDatalist(rollInputId, sessionInputId) {
        const rollInput = document.getElementById(rollInputId);
        const sessionInput = document.getElementById(sessionInputId);
        const datalist = document.getElementById('session-list');
        
        rollInput.addEventListener('input', () => {
            const sessions = generateSessionsList(rollInput.value);
            if (sessions.length > 0) {
                datalist.innerHTML = '';
                sessions.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s;
                    datalist.appendChild(opt);
                });
                
                if (!sessionInput.dataset.manuallyEdited) {
                    sessionInput.value = sessions[0];
                }
            }
        });
        
        sessionInput.addEventListener('input', () => {
            sessionInput.dataset.manuallyEdited = "true";
        });
    }

    updateSessionDatalist('single-roll', 'single-session');
    updateSessionDatalist('batch-start', 'batch-session');

    // Handle Fetch All Checkbox
    const fetchAllCheckbox = document.getElementById('single-fetch-all');
    const singleSessionContainer = document.getElementById('single-session-container');
    const singleSessionInput = document.getElementById('single-session');
    
    fetchAllCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            singleSessionContainer.style.display = 'none';
            singleSessionInput.removeAttribute('required');
        } else {
            singleSessionContainer.style.display = 'block';
            singleSessionInput.setAttribute('required', 'true');
        }
    });

    // Handle Single Student Fetch
    const singleForm = document.getElementById('single-form');
    singleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = singleForm.querySelector('.submit-btn');
        btn.classList.add('btn-loading');
        setRightPaneView('placeholder'); // Clear right pane temporarily
        
        const payload = {
            rollNo: document.getElementById('single-roll').value,
            session: document.getElementById('single-session').value,
            fetchAll: document.getElementById('single-fetch-all').checked
        };

        try {
            const response = await fetch('/api/fetch-single', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            if (data.student_info) {
                renderResults(data);
                setRightPaneView('single');
            } else {
                alert("Failed to fetch results or no records found.");
            }
        } catch (error) {
            alert("Network error: " + error.message);
        } finally {
            btn.classList.remove('btn-loading');
        }
    });

    // Handle Batch Student Fetch
    const batchForm = document.getElementById('batch-form');
    batchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = batchForm.querySelector('.submit-btn');
        btn.classList.add('btn-loading');
        
        const downloadBtn = document.getElementById('download-excel-btn');
        const branchesContainer = document.getElementById('batch-branches-container');
        const errorsContainer = document.getElementById('batch-errors-container');
        const errorsLog = document.getElementById('batch-errors-log');
        
        setRightPaneView('batch');
        downloadBtn.style.display = 'none';
        branchesContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">Initiating batch fetch...</div>';
        errorsContainer.style.display = 'none';
        errorsLog.innerHTML = '';
        
        const payload = {
            startRoll: document.getElementById('batch-start').value,
            endRoll: document.getElementById('batch-end').value,
            session: document.getElementById('batch-session').value
        };

        try {
            const response = await fetch('/api/start-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            if (data.task_id) {
                // Reset UI
                batchActive = true;
                const branchesContainer = document.getElementById('batch-branches-container');
                const errorsContainer = document.getElementById('batch-errors-container');
                const errorsLog = document.getElementById('batch-errors-log');
                
                branchesContainer.innerHTML = '';
                errorsContainer.style.display = 'none';
                errorsLog.innerHTML = '';
                // 'downloadBtn' is already declared in the outer scope
                downloadBtn.style.display = 'none';
                
                let branches = {}; 
                
                const renderBranchSection = (branchName) => {
                    const branchData = branches[branchName];
                    const safeId = branchName.replace(/[^a-zA-Z0-9]/g, '_');
                    
                    let container = document.getElementById(`branch-section-${safeId}`);
                    if (!container) {
                        container = document.createElement('div');
                        container.id = `branch-section-${safeId}`;
                        container.className = "glass-panel";
                        container.style.padding = "20px";
                        container.style.background = "rgba(0,0,0,0.2)";
                        
                        branchesContainer.appendChild(container);
                    }
                    
                    // Calculate Top 3 (sorted by SGPA)
                    const top3 = [...branchData.students].sort((a, b) => b.sgpa - a.sgpa).slice(0, 3);
                    
                    // Sort the main table by Roll No (Registration Number)
                    branchData.students.sort((a, b) => a.rollNo.localeCompare(b.rollNo));
                    
                    let lbHtml = '<div class="leaderboard-grid" style="margin-bottom: 20px;">';
                    top3.forEach((s, index) => {
                        const rank = index + 1;
                        lbHtml += `
                            <div class="topper-card rank-${rank}">
                                <div class="topper-rank">#${rank}</div>
                                <div class="topper-name" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">${s.name}</div>
                                <div class="topper-sgpa">${s.sgpa.toFixed(2)}</div>
                            </div>
                        `;
                    });
                    lbHtml += '</div>';
                    
                    // Render Table
                    let tableHtml = `
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; white-space: nowrap;">
                                <thead>
                                    <tr style="background: rgba(0,0,0,0.3); border-bottom: 1px solid var(--border-glass); color: var(--text-secondary);">
                                        <th style="padding: 10px; text-align: left;">Roll No</th>
                                        <th style="padding: 10px; text-align: left;">Name</th>
                                        <th style="padding: 10px;">SGPA</th>
                    `;
                    
                    branchData.subjectCodes.forEach(code => {
                        const title = branchData.subjectMap[code] || code;
                        tableHtml += `<th style="padding: 10px;" title="${title}">${code}</th>`;
                    });
                    
                    tableHtml += `
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    branchData.students.forEach((s, i) => {
                        const bg = i % 2 === 0 ? 'background: rgba(255,255,255,0.02);' : '';
                        let sgpaColor = 'var(--text-primary)';
                        if (s.sgpa >= 8) sgpaColor = '#4ADE80';
                        else if (s.sgpa >= 6) sgpaColor = '#FCD34D';
                        else sgpaColor = '#F87171';
                        
                        tableHtml += `
                            <tr style="${bg} border-bottom: 1px solid rgba(255,255,255,0.02); transition: background 0.2s;">
                                <td style="padding: 8px 10px; text-align: left; font-family: monospace;">${s.rollNo}</td>
                                <td style="padding: 8px 10px; text-align: left; font-weight: 500; max-width: 150px; overflow: hidden; text-overflow: ellipsis;" title="${s.name}">${s.name}</td>
                                <td style="padding: 8px 10px; font-weight: bold; color: ${sgpaColor};">${s.sgpa.toFixed(2)}</td>
                        `;
                        
                        branchData.subjectCodes.forEach(code => {
                            const grade = s.grades[code] || '—';
                            let gColor = 'var(--text-muted)';
                            if (['O', 'E'].includes(grade)) gColor = '#4ADE80';
                            else if (['F', 'M', 'F(Ex)'].includes(grade)) gColor = '#F87171';
                            else if (grade !== '—') gColor = 'var(--text-primary)';
                            
                            tableHtml += `<td style="padding: 8px 10px; color: ${gColor}; font-weight: ${gColor !== 'var(--text-muted)' ? '600' : 'normal'};">${grade}</td>`;
                        });
                        
                        tableHtml += `</tr>`;
                    });
                    
                    tableHtml += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    container.innerHTML = `
                        <h3 style="margin-bottom: 16px; color: var(--text-primary); font-size: 16px; display: flex; align-items: center; gap: 8px;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                            ${branchName}
                        </h3>
                        ${top3.length > 0 ? lbHtml : ''}
                        ${tableHtml}
                    `;
                };
                
                const eventSource = new EventSource(`/api/stream-batch?task_id=${data.task_id}`);
                
                eventSource.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);
                        
                        if (msg.type === 'progress') {
                            const res = msg.data;
                            
                            if (res.status === "SUCCESS") {
                                const info = res.student_info || {};
                                const branchName = info.branchName || "Unknown Branch";
                                const name = info.studentName || "N/A";
                                
                                if (!branches[branchName]) {
                                    branches[branchName] = { subjectCodes: [], subjectMap: {}, students: [] };
                                }
                                
                                const gradesData = res.grades_data || {};
                                const sgpaRaw = gradesData.sgpadetails ? gradesData.sgpadetails.sgpa : "0.0";
                                const sgpa = parseFloat(sgpaRaw) || 0.0;
                                
                                const gradesList = gradesData.grades || [];
                                const gradesDict = {};
                                
                                gradesList.forEach(g => {
                                    const code = g.subjectCODE;
                                    if (code) {
                                        gradesDict[code] = g.grade;
                                        if (!branches[branchName].subjectCodes.includes(code)) {
                                            branches[branchName].subjectCodes.push(code);
                                            branches[branchName].subjectMap[code] = g.subjectName;
                                        }
                                    }
                                });
                                
                                branches[branchName].students.push({
                                    rollNo: res.roll_no,
                                    name: name,
                                    sgpa: sgpa,
                                    grades: gradesDict
                                });
                                
                                renderBranchSection(branchName);
                                
                            } else {
                                errorsContainer.style.display = 'block';
                                const rowHtml = `
                                    <div style="display: grid; grid-template-columns: 120px 1fr 100px; gap: 12px; padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.02); font-size: 13px;">
                                        <div style="font-family: monospace; color: var(--text-primary);">${res.roll_no}</div>
                                        <div style="color: var(--text-secondary);">${res.error || 'Failed'}</div>
                                        <div><span class="badge ${res.status === 'NO_PROFILE' ? 'warning-badge' : 'danger-badge'}">${res.status}</span></div>
                                    </div>
                                `;
                                errorsLog.innerHTML += rowHtml;
                                errorsLog.scrollTop = errorsLog.scrollHeight;
                            }
                        } else if (msg.type === 'done') {
                            eventSource.close();
                            batchActive = false;
                            btn.classList.remove('btn-loading');
                            downloadBtn.href = `/api/download/${msg.filename}`;
                            downloadBtn.style.display = 'inline-flex';
                            fetchExports(); // Auto refresh exports tab
                        } else if (msg.type === 'error') {
                            eventSource.close();
                            batchActive = false;
                            btn.classList.remove('btn-loading');
                            errorsContainer.style.display = 'block';
                            errorsLog.innerHTML += `
                                <div style="color: #F87171; padding: 12px; font-weight: bold; background: rgba(248,113,113,0.1);">
                                    Fatal Error: ${msg.message}
                                </div>
                            `;
                            errorsLog.scrollTop = errorsLog.scrollHeight;
                        }
                    } catch (e) {
                        console.error('SSE Error:', e);
                    }
                };
            }
        } catch (error) {
            alert("Error starting batch: " + error.message);
            btn.classList.remove('btn-loading');
        }
    });

    // Fetch and display Past Exports
    async function fetchExports() {
        const listContainer = document.getElementById('exports-list');
        listContainer.innerHTML = '<div class="spinner" style="display:block; border-color:rgba(255,255,255,0.1); border-top-color:#6366F1;"></div>';
        
        try {
            const res = await fetch('/api/exports');
            const data = await res.json();
            
            listContainer.innerHTML = '';
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const a = document.createElement('a');
                    a.href = `/api/download/${file}`;
                    a.className = "tab-btn";
                    a.style.display = "block";
                    a.style.textAlign = "left";
                    a.style.padding = "10px 16px";
                    a.style.background = "rgba(0,0,0,0.2)";
                    a.style.textDecoration = "none";
                    a.style.marginBottom = "5px";
                    a.innerText = "📄 " + file;
                    
                    a.addEventListener('mouseover', () => a.style.background = "rgba(99, 102, 241, 0.2)");
                    a.addEventListener('mouseout', () => a.style.background = "rgba(0,0,0,0.2)");
                    
                    listContainer.appendChild(a);
                });
            } else {
                listContainer.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No past exports found.</p>';
            }
        } catch (e) {
            listContainer.innerHTML = '<p style="color: #F87171; font-size: 13px;">Failed to load exports.</p>';
        }
    }

    // UI Rendering Logic for Single Student
    function renderResults(data) {
        const profile = document.getElementById('student-profile');
        const gradesContainer = document.getElementById('grades-container');
        const analyticsCard = document.getElementById('analytics-card');
        
        const info = data.student_info;
        
        profile.innerHTML = `
            <div>
                <h2 style="font-size: 26px; color: #fff; margin-bottom: 4px;">${info.studentName}</h2>
                <p style="color: var(--text-secondary); font-size: 15px;">Roll No: <strong style="color: #fff">${info.rollNo}</strong> | Branch: ${info.branchName}</p>
                <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">College: ${info.collegeName}</p>
            </div>
        `;
        
        gradesContainer.innerHTML = '';
        analyticsCard.style.display = 'none';
        analyticsCard.innerHTML = '';
        
        // Data for Chart.js
        const chartLabels = [];
        const chartData = [];
        
        if (data.results && data.results.length > 0) {
            // Helper to get a chronological score for a session like "Odd-(2022-23)"
            const getSessionScore = (sessionStr) => {
                const match = (sessionStr || "").match(/(Odd|Even)-\((\d{4})-\d{2}\)/);
                if (match) {
                    const season = match[1];
                    const year = parseInt(match[2]);
                    return year * 10 + (season === "Odd" ? 0 : 1);
                }
                return 0;
            };

            // Chronological sort: by session time, then by semId
            const sortedResults = [...data.results].sort((a, b) => {
                const scoreA = getSessionScore(a.examSession);
                const scoreB = getSessionScore(b.examSession);
                if (scoreA !== scoreB) return scoreA - scoreB;
                return parseInt(a.semId || 0) - parseInt(b.semId || 0);
            });

            // ANALYTICS CALCULATION: Track the latest status of every unique subject
            const subjectHistory = {};
            
            sortedResults.forEach(semData => {
                const detailed = semData.detailed_grades || {};
                
                // Add to chart data (this keeps the chart chronological)
                const sgpaRaw = detailed.sgpadetails ? detailed.sgpadetails.sgpa : "0.0";
                const sgpa = parseFloat(sgpaRaw) || 0.0;
                chartLabels.push(semData.semester);
                chartData.push(sgpa);
                
                // Track latest grades
                if (detailed.grades && detailed.grades.length > 0) {
                    detailed.grades.forEach(g => {
                        const pts = parseFloat(g.points) || 0;
                        const creds = parseFloat(g.subjectCredits) || 0;
                        subjectHistory[g.subjectCODE] = {
                            code: g.subjectCODE,
                            name: g.subjectName,
                            grade: g.grade,
                            points: pts,
                            credits: creds
                        };
                    });
                }
                
                // Render the individual semester tables (UI logic)
                const semWrapper = document.createElement('div');
                semWrapper.style.background = "rgba(0,0,0,0.15)";
                semWrapper.style.padding = "16px";
                semWrapper.style.borderRadius = "var(--radius-md)";
                semWrapper.style.border = "1px solid var(--border-glass)";
                
                let html = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
                        <h3 style="font-size: 16px; color: var(--accent-secondary);">${semData.semester} Semester <span style="font-size:12px; color:var(--text-muted);">(${semData.examSession})</span></h3>
                        <span style="font-weight: 600; background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 4px 10px; border-radius: 4px; font-size: 14px;">SGPA: ${sgpaRaw}</span>
                    </div>
                `;
                
                if (detailed.grades && detailed.grades.length > 0) {
                    html += `
                        <div style="display: grid; grid-template-columns: 1fr 60px; gap: 8px; border-bottom: 1px solid var(--border-glass); padding-bottom: 8px; margin-bottom: 8px; font-size: 12px; color: var(--text-muted);">
                            <div>Subject</div>
                            <div style="text-align: center;">Grade</div>
                        </div>
                    `;
                    
                    detailed.grades.forEach(g => {
                        let badgeClass = "info-badge";
                        if (["O", "E", "A", "B", "C"].includes(g.grade)) badgeClass = "success-badge";
                        else if (g.grade === "D") badgeClass = "warning-badge";
                        else if (["F", "M", "F(Ex)"].includes(g.grade)) badgeClass = "danger-badge";
                        
                        html += `
                            <div style="display: grid; grid-template-columns: 1fr 60px; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.02);">
                                <div style="font-size: 13px; color: var(--text-primary);">${g.subjectName} <span style="color: var(--text-muted); font-size: 11px;">(${g.subjectCODE})</span></div>
                                <div style="text-align: center;"><span class="badge ${badgeClass}">${g.grade}</span></div>
                            </div>
                        `;
                    });
                } else {
                    html += `<p style="font-size: 13px; color: var(--text-muted);">No grades found.</p>`;
                }
                
                semWrapper.innerHTML = html;
                gradesContainer.appendChild(semWrapper);
            });
            
            // Render Analytics Card
            let totalCredits = 0;
            let totalCreditPoints = 0;
            const activeBacklogs = [];
            
            Object.values(subjectHistory).forEach(s => {
                if (s.credits > 0) {
                    totalCredits += s.credits;
                    totalCreditPoints += (s.credits * s.points);
                }
                if (s.points === 0 && ["F", "M", "F(Ex)", "ABS"].includes(s.grade)) {
                    activeBacklogs.push(s);
                }
            });
            
            const estimatedCGPA = totalCredits > 0 ? (totalCreditPoints / totalCredits).toFixed(2) : "0.00";
            
            let statusHtml = "";
            if (activeBacklogs.length === 0) {
                statusHtml = `
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="background: rgba(74, 222, 128, 0.2); color: #4ADE80; padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid rgba(74, 222, 128, 0.3); font-weight: 600; font-size: 14px;">
                            ✅ ALL CLEAR
                        </div>
                        <span style="color: var(--text-secondary); font-size: 13px;">No active backlogs found.</span>
                    </div>
                `;
            } else {
                let backlogList = activeBacklogs.map(b => `<span style="display: inline-block; background: rgba(248, 113, 113, 0.1); color: #F87171; padding: 2px 6px; border-radius: 4px; font-size: 11px; border: 1px solid rgba(248, 113, 113, 0.2); margin-right: 6px; margin-bottom: 6px;">${b.name} (${b.code})</span>`).join('');
                statusHtml = `
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="background: rgba(248, 113, 113, 0.2); color: #F87171; padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid rgba(248, 113, 113, 0.3); font-weight: 600; font-size: 14px;">
                                ⚠️ ${activeBacklogs.length} ACTIVE BACKLOG(S)
                            </div>
                        </div>
                        <div style="margin-top: 4px;">${backlogList}</div>
                    </div>
                `;
            }
            
            analyticsCard.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div style="flex: 1;">
                        ${statusHtml}
                    </div>
                    <div style="text-align: right; background: rgba(0,0,0,0.3); padding: 12px 20px; border-radius: var(--radius-sm); border: 1px solid var(--border-glass);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;">Estimated CGPA</div>
                        <div style="font-size: 28px; font-weight: 700; color: #fff;">${estimatedCGPA}</div>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Total Credits: ${totalCredits}</div>
                    </div>
                </div>
            `;
            analyticsCard.style.display = 'block';
            
            renderChart(chartLabels, chartData);
        } else {
            gradesContainer.innerHTML = `<p style="text-align: center; color: var(--text-muted);">No results found.</p>`;
            if (sgpaChartInstance) {
                sgpaChartInstance.destroy();
                sgpaChartInstance = null;
            }
        }
    }

    // Chart.js Rendering logic
    function renderChart(labels, dataPoints) {
        const ctx = document.getElementById('sgpa-chart').getContext('2d');
        
        if (sgpaChartInstance) {
            sgpaChartInstance.destroy();
        }
        
        // Gradient fill
        let gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)'); // --accent-primary
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');
        
        sgpaChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'SGPA',
                    data: dataPoints,
                    borderColor: '#6366F1', // --accent-primary
                    backgroundColor: gradient,
                    borderWidth: 2,
                    pointBackgroundColor: '#0EA5E9', // --accent-secondary
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false,
                        },
                        ticks: {
                            color: '#94A3B8'
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                            drawBorder: false,
                        },
                        ticks: {
                            color: '#94A3B8'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 34, 45, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#4ADE80',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `SGPA: ${context.parsed.y}`;
                            }
                        }
                    }
                }
            }
        });
    }
});
