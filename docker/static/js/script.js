const initialHTML = "<p id='select-song' class='song-name blink-slow'>노래를 선택합시다</p><p class='large'>____</p>";
const defaultTitleBarMessage = "화면반주가상체계《메아리》";
const defaultEventName = "조선화면반주음악대회";
const museColours = ["--ll-maki", "--ll-honoka", "--ll-rin", "--ll-hanayo", "--ll-eli", "--ll-umi", "--ll-nozomi", "--ll-nico", "--ll-kotori"];

function getRandomColour() {
    const randomColourIndex = Math.floor(Math.random() * museColours.length);
    return museColours[randomColourIndex];
}

const sessionState = {
    inputNumber: "",
    songInfo: {},
    remarks: "",
    duration: "",
    pitch: 0,
    historyDocId: null,
    currentPreviewAudio: null,
    countdown: null,
    latestEvent : null,
    titleBarTimer: null
};

document.addEventListener("DOMContentLoaded", () => {
    const audio = document.getElementById("audio");
    const inputBox = document.getElementById("input-box");
    const selectSongMsg = document.getElementById("select-song");
    const video = document.getElementById("video");
    const scrollBg = document.getElementById("scroll-background");
    const scrollingDiv = document.getElementById("scrolling-history");
    const launchImg = document.getElementById("launch-image");
    const startButton = document.getElementById("start-button");

    let versionInfo = null;
    let discordNotification = [];

    /* 尊名を太字に */
    function highlightGreatLeaders(text) {
        const names = ["김일성", "김정일", "김정은"];
        names.forEach(name => {
            const regex = new RegExp(name, "g");
            text = text.replace(regex, `<span class="great-leader">${name}</span>`);
        });
        return text;
    }

    /* 背景画像設定 */
    function setBackground(image) {
        document.body.style.backgroundImage = `url(${image})`;
    }
    
    function updateTitleBarContent(messages) {
        const titleBar = document.getElementById("video-title");

        if (!Array.isArray(messages) || messages.length === 0) return;

        if (sessionState.titleBarTimer !== null) {
            clearTimeout(sessionState.titleBarTimer);
        }

        let index = 0;
        let active = true;  // タイマーの生存状態フラグ

        function showNextMessage() {
            if (!active) return;

            titleBar.classList.remove("slide-from-top");
            titleBar.classList.add("fade-out");

            setTimeout(() => {
                if (!active) return;

                titleBar.innerHTML = messages[index];
                let randomColour = getRandomColour();
                titleBar.style.color = `color-mix(in srgb, white 40%, var(${randomColour}) 60%)`;
                titleBar.style.textShadow = `0 0 0.25rem var(${randomColour})`;
                titleBar.classList.remove("fade-out");
                titleBar.classList.add("slide-from-top");

                index = (index + 1) % messages.length;
                if (messages.length > 1) {
                    sessionState.titleBarTimer = setTimeout(showNextMessage, 18000);
                }
            }, 500);
        }

        // 前のタイマーを完全に無効化
        if (typeof sessionState.titleBarCancel === "function") {
            sessionState.titleBarCancel();
        }

        sessionState.titleBarCancel = () => {
            active = false;
            clearTimeout(sessionState.titleBarTimer);
        };

        showNextMessage();
    }

    /* 変数初期化 */
    function initVariables() {
        sessionState.inputNumber = "";
        sessionState.songInfo = {};
        sessionState.remarks = "";
        sessionState.duration = "";
        sessionState.pitch = 0;
        sessionState.historyDocId = null;
        sessionState.titleBarTimer = null;
    }

    function getVersionInfo() {
        return fetch("/about")
            .then(res => res.json())
            .then(version => {
                versionInfo = version;
            });
    }

    function getEventInfo() {
        return fetch("/event-info")
            .then(res => {
                if (res.status === 204) {
                    // 該当イベントなし
                    return null;
                }
                return res.json();
            })
            .then(eventInfo => {
                if (eventInfo) {
                    sessionState.latestEvent = `제${eventInfo.eventNumber}차대회(${eventInfo.location})`;
                } else {
                    sessionState.latestEvent = null;
                };
            });
    }

    function fetchDiscordNotifications() {
        fetch("/notify/list")
            .then(response => response.json())
            .then(data => {
                if (Array.isArray(data)) {
                    discordNotification = data;
                    console.log("通知メッセージ更新:", discordNotification);
                }
            })
            .catch(error => {
                console.error("通知メッセージの取得エラー:", error);
            });
    }

    fetchDiscordNotifications();
    setInterval(fetchDiscordNotifications, 60000);

    /* 予約曲問い合わせ */
    function fetchNextReservedSong() {
        return fetch("/next_reserved_song")
            .then(response => response.json())
            .catch(error => {
                console.error("予約システム問い合わせ失敗:", error);
                return { has_next: false };
            });
    }

    function sendPlaybackEvent(eventType) {
        fetch(`/control/${eventType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                songNumber: sessionState.inputNumber,
                pitch: sessionState.pitch
            })
        }).catch(err => console.error(`Failed to send ${eventType}:`, err));
    }

    function createHistoryRecord() {
        const createdAt = Math.floor(Date.now() / 1000);
        return fetch("/history/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                songNumber: sessionState.inputNumber,
                pitch: sessionState.pitch,
                created_at: createdAt
            })
        })
        .then(res => res.json())
        .then(data => {
            sessionState.historyDocId = data.docId;
        })
        .catch(err => {
            console.error("履歴の新規作成エラー:", err);
        });
    }
    
    function updateHistory(status) {
        if (!sessionState.historyDocId) {
            console.warn("historyDocId が未設定のため、履歴更新をスキップ");
            return;
        }

        const createdAt = Math.floor(Date.now() / 1000);
        const payload = {
            status: status,
            created_at: createdAt
        };

        if (status === "playStarted") {
            payload.pitch = sessionState.pitch;  // pitchを追加
        }

        fetch(`/history/update/${sessionState.historyDocId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .catch(err => console.error(`履歴更新（${status}）失敗:`, err));
    }

    /* 起動画面 */
    function resetToStartup() {
        inputBox.style.color = "white";
        scrollBg.style.display = "none";
        initVariables();
        getVersionInfo().then(() => {
            inputBox.innerHTML = `<p>${versionInfo.name}</p><p>Version ${versionInfo.version}</p><span class='lyrics'>${versionInfo.owner}</span>`;
            setBackground("static/background/title.png");
            audio.play();
            setTimeout(() => {
                setBackground("static/background/input_blank.png");
                inputBox.innerHTML = initialHTML;
                const selectSongMsg = document.getElementById("select-song");
                selectSongMsg.style.color = `color-mix(in srgb, white 30%, var(${getRandomColour()}) 70%)`;
            }, 5000);
        });
    }

    /* 選曲画面 */
    function resetToSelection() {
        inputBox.style.color = "white";
        initVariables();
        inputBox.innerHTML = initialHTML;
        const selectSongMsg = document.getElementById("select-song");
        selectSongMsg.style.color = `color-mix(in srgb, white 30%, var(${getRandomColour()}) 70%)`;
        scrollBg.style.display = "none";
        scrollingDiv.style.display = "none";
        updateTitleBarContent(sessionState.latestEvent? [defaultEventName, sessionState.latestEvent]: [defaultTitleBarMessage]);
        setBackground("static/background/input_blank.png");
    }

    async function afterTimer() {
        video.style.display = "none";
        inputBox.style.color = "white";
        setBackground("static/background/input_blank.png");
        inputBox.innerHTML = "예약정보수신중...";
        sendPlaybackEvent("playEnded");
        initVariables();
    
        const next = await fetchNextReservedSong();
        if (next.has_next && next.song && next.song.songNumber) {
            sessionState.inputNumber = next.song.songNumber;
            checkSong();
        } else {
            resetToSelection();
        }
    };

    function playSoundEffect(filename) {
        try {
            const sound = new Audio(`static/sounds/${filename}`);
            sound.play().catch(error => console.error("音声再生エラー:", error));
        } catch (error) {
            console.error("playSound() でエラー:", error);
        }
    }

    function formatSeconds(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        const formattedSeconds = remainingSeconds.toString().padStart(2, '0');
        return `${minutes}:${formattedSeconds}`;
    }

    function generateRemarksFromSong(songInfo) {
        let remarks_array = [];
        let lyricist = songInfo.lyricist || "";
        let composer = songInfo.composer || "";
        let lyricStart = highlightGreatLeaders(songInfo.lyricStart || "");
        console.log(songInfo);

        sessionState.duration = formatSeconds(songInfo.duration);
    
        if (lyricist && composer) {
            if (lyricist === composer) {
                remarks_array.push(`<span class='border'>작사,작곡</span> ${lyricist}`);
            } else {
                remarks_array.push(`<span class='border'>작사</span> ${lyricist}`);
                remarks_array.push(`<span class='border'>작곡</span> ${composer}`);
            }
        } else if (lyricist) {
            remarks_array.push(`<span class='border'>작사</span> ${lyricist}`);
        } else if (composer) {
            remarks_array.push(`<span class='border'>작곡</span> ${composer}`);
        }

        if (songInfo.songKey) {
            remarks_array.push(`<span class='border'>조성</span> ${songInfo.songKey}`)
        };

        sessionState.remarks = lyricStart
            ? `<span class='lyrics fade-in'>♫ ${lyricStart}</span><br><span class='remarks'>${remarks_array.join(" ")}</span>`
            : `<span class='remarks'>${remarks_array.join(" ")}</span>`;
    }

    /* 曲存在確認、再生準備画面 */
    function checkSong() {
        if (sessionState.inputNumber.startsWith("98")) {
            const minutes = parseInt(sessionState.inputNumber.slice(2), 10);
            if (!isNaN(minutes)) {
                startTimerWithBGM(minutes);
                return;
            }
        }

        fetch(`/song_info/${sessionState.inputNumber}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.songName) {
                    sessionState.songInfo = data;
                    generateRemarksFromSong(sessionState.songInfo);
                    createHistoryRecord().then(() => {
                        showPitchSelection();
                        playPreview(sessionState.inputNumber);
                    });
                } else {
                    sessionState.inputNumber = "";
                    sessionState.songInfo = {};
                    inputBox.innerHTML = "<p class='large'>____</p>";
                }
            })
            .catch(error => console.error("曲リスト取得エラー:", error));
    }

    /* 休憩時の履歴表示 */
    function updateScrollingHistory() {
        fetch("/history")
            .then(res => res.json())
            .then(historyList => {
                const recentSongs = historyList.recent.slice(0, 5);
                const playedCount = `〈총재생곡수〉 ${historyList.totalCount} `;

                const text = playedCount + "〈최근 부른 노래〉" + recentSongs.map(item =>
                    `<span class='border'>${item.songNumber}</span> ${highlightGreatLeaders(item.songTitle)}`
                ).join(" / ");

                scrollingDiv.innerHTML = text;
                scrollBg.style.display = "block";
                scrollingDiv.style.display = "block";
            })
            .catch(err => console.error("履歴取得エラー:", err));
    }

    /* 休憩タイマー */
    function startTimerWithBGM(minutes) {
        const totalSeconds = minutes * 60;
        let remainingSeconds = totalSeconds;

        inputBox.innerHTML = `<p class='song-name'>휴식시간</p><p class='large'>${minutes}분</p>`;

        fetch("/bgm_list")
            .then(res => res.json())
            .then(fileList => {
                if (!Array.isArray(fileList) || fileList.length === 0) {
                    console.error("BGM音源がありません");
                    return;
                }

                fileList = fileList.sort(() => Math.random() - 0.5);

                let currentIndex = 0;
                sessionState.currentPreviewAudio = new Audio(`/bgm/${fileList[currentIndex]}`);
                sessionState.currentPreviewAudio.volume = 0.3;
                sessionState.currentPreviewAudio.play();
                updateScrollingHistory();

                const playNext = () => {
                    currentIndex = (currentIndex + 1) % fileList.length;
                    sessionState.currentPreviewAudio.src = `/bgm/${fileList[currentIndex]}`;
                    sessionState.currentPreviewAudio.play();
                };

                sessionState.currentPreviewAudio.addEventListener("ended", playNext);

                sessionState.countdown = setInterval(() => {
                    remainingSeconds--;
                    inputBox.innerHTML = `<p class='song-name'>휴식시간</p><p class='large'>${Math.floor(remainingSeconds / 60)}:${(remainingSeconds % 60).toString().padStart(2, '0')}</p>`;
                    if (remainingSeconds <= 0) {
                        clearInterval(sessionState.countdown);
                        sessionState.countdown = null;
                        sessionState.currentPreviewAudio.pause();
                        sessionState.currentPreviewAudio = null;
                        inputBox.innerHTML = "<p>휴식시간이 다 됐습니다</p>";
                        setTimeout(afterTimer, 3000);
                    }
                }, 1000);
            });
    }

    /* 再生準備画面の文字情報 */
    function generateSongSelectedHTML() {
        const pitchDisplay = sessionState.pitch > 0 ? `+${sessionState.pitch}` : sessionState.pitch.toString();
        return `<p>${sessionState.inputNumber}</p><p class='song-name'>${highlightGreatLeaders(sessionState.songInfo.songName)}</p><p>${sessionState.remarks}</p><p>${sessionState.duration} | 음정 ${pitchDisplay}</p>`;
    }

    /* 再生準備画面 */
    function showPitchSelection() {
        setBackground("static/background/input_blank.png");
        inputBox.innerHTML = generateSongSelectedHTML();
    }

    function stopPreview() {
        if (sessionState.currentPreviewAudio) {
            sessionState.currentPreviewAudio.pause();
            sessionState.currentPreviewAudio.currentTime = 0;
            sessionState.currentPreviewAudio = null;
        }
    }

    function playPreview(songNumber, pitch = 0, start = null, duration = 8) {
        if (sessionState.currentPreviewAudio) {
            stopPreview();
        }

        const params = new URLSearchParams();
        params.set("pitch", pitch);
        if (start !== null) params.set("start", start);
        if (duration !== null) params.set("duration", duration);
    
        const previewAudio = new Audio(`/preview/${songNumber}?${params.toString()}`);
        previewAudio.volume = 0.5;
        previewAudio.play().catch(error => console.error("プレビュー音声再生エラー:", error));

        sessionState.currentPreviewAudio = previewAudio;
    }

    /* 動画問い合わせ */
    function startConversion() {
        inputBox.innerHTML += "<p class='lyrics blink-fast' style='background:white;'>내리적재중...Downloading Video</p>"
        if (sessionState.pitch !== 0) {
            if (sessionState.currentPreviewAudio) {
                stopPreview();
            };
            sessionState.currentPreviewAudio = new Audio("static/sounds/wait2.mp3");
            sessionState.currentPreviewAudio.play().catch(error => console.error("変換中音声再生エラー:", error));;
        };
        fetch("/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ song_number: sessionState.inputNumber, pitch: sessionState.pitch })
        })
            .then(response => response.json())
            .then(data => {
                if (data.processed_file) {
                    playVideo(data.processed_file);
                } else {
                    console.error("変換エラー:", data);
                }
            })
            .catch(error => console.error("変換リクエストエラー:", error));
    }

    /* 再生開始 */
    function playVideo(filename) {
        if (sessionState.currentPreviewAudio) {
            stopPreview();
        };
    
        document.body.style.backgroundImage = "none";
        inputBox.innerHTML = "";
        inputBox.style.color = "transparent";
        video.src = filename;
        video.style.display = "block";
        updateTitleBarContent([highlightGreatLeaders(sessionState.songInfo.songName), defaultTitleBarMessage]);

        video.play().then(() => {
            updateHistory("playStarted");
            video.onended = async () => {
                video.style.display = "none";
                updateTitleBarContent(sessionState.latestEvent? [defaultEventName, sessionState.latestEvent]: [defaultTitleBarMessage]);
                inputBox.style.color = "white";
                setBackground("static/background/input_blank.png");
                inputBox.innerHTML = "예약정보수신중...";
                updateHistory("playFinished");
                initVariables();
    
                const next = await fetchNextReservedSong();
                if (next.has_next && next.song && next.song.songNumber) {
                    sessionState.inputNumber = next.song.songNumber;
                    checkSong();
                } else {
                    resetToSelection();
                }
            };
        }).catch(err => {
            console.error("動画再生エラー:", err);
        });
    }

    /* 右上の時計 */
    function updateClock() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        document.getElementById('clock').textContent = `${hours}:${minutes}:${seconds}`;
    }

    setInterval(updateClock, 1000);
    getEventInfo();
    updateTitleBarContent(sessionState.latestEvent? [defaultEventName, sessionState.latestEvent]: [defaultTitleBarMessage]);
    updateClock();

    startButton.addEventListener("click", () => {
        startButton.style.display = "none";
        launchImg.style.display = "none";
        resetToStartup();
    });

    /* キーバインド */
    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {
            if (sessionState.countdown !== null) {
                clearInterval(sessionState.countdown);
                sessionState.countdown = null;
            }
            if (sessionState.currentPreviewAudio !== null) {
                sessionState.currentPreviewAudio.pause();
                sessionState.currentPreviewAudio = null;
            }

            if (!video.paused && video.currentTime > 0) {
                video.pause();
                updateHistory("playAborted");
            } else if (sessionState.inputNumber.length === 4 && !video.src) {
                updateHistory("songCancelled");
            }
            
            stopPreview();
            video.currentTime = 0;
            video.style.display = "none";
            resetToSelection();
        }

        if (event.key >= "0" && event.key <= "9" && sessionState.inputNumber.length < 4) {
            sessionState.inputNumber += event.key;
            inputBox.innerHTML = `<p class='large'>${"____".slice(sessionState.inputNumber.length) + sessionState.inputNumber}</p>`;
            playSoundEffect(`${event.key}.mp3`);
            if (sessionState.inputNumber.length === 4) {
                checkSong();
            }
        } else if (event.key === "+" && sessionState.pitch < 8) {
            sessionState.pitch++;
            inputBox.innerHTML = generateSongSelectedHTML();
            playSoundEffect(`plus.mp3`);
            playPreview(sessionState.inputNumber, sessionState.pitch);
        } else if (event.key === "-" && sessionState.pitch > -8) {
            sessionState.pitch--;
            inputBox.innerHTML = generateSongSelectedHTML();
            playSoundEffect(`minus.mp3`);
            playPreview(sessionState.inputNumber, sessionState.pitch);
        } else if (event.key === "Enter" && sessionState.inputNumber.length === 4) {
            startConversion();
            playSoundEffect("enter.mp3");
        }
    });

    console.log("《발사준비 끝!》");
});

