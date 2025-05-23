const initialHTML = "<p class='song-name blink-slow'>노래를 선택합시다</p><p class='large'>____</p>"

document.addEventListener("DOMContentLoaded", () => {
    const audio = document.getElementById("audio");
    const inputBox = document.getElementById("input-box");
    const video = document.getElementById("video");
    const scrollBg = document.getElementById("scroll-background");
    const scrollingDiv = document.getElementById("scrolling-history");
    const launchImg = document.getElementById("launch-image");
    const startButton = document.getElementById("start-button");

    let historyDocId = null;
    let countdown = null;
    let bgmPlayer = null;
    let waitMusic = null;
    let inputNumber = "";
    let songInfo = {};
    let versionInfo = {};
    let latestEvent = null;
    let remarks = "";
    let duration = "";
    let pitch = 0;

    let currentPreviewAudio = null;

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

    /* 変数初期化 */
    function initVariables() {
        inputNumber = "";
        songInfo = {};
        remarks = "";
        duration = "";
        pitch = 0;
        historyDocId = null;
    }

    /* バージョン情報 */
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
                    latestEvent = `제${eventInfo.eventNumber}차대회 ${eventInfo.location} - `
                } else {
                    latestEvent = ""
                };
            });
    }

    /* 予約曲問い合わせ */
    function fetchNextReservedSong() {
        return fetch("/next_reserved_song")
            .then(response => response.json())
            .catch(error => {
                console.error("予約システム問い合わせ失敗:", error);
                return { has_next: false };
            });
    }
    
    /* 再生状態報告 */
    function sendPlaybackEvent(eventType) {
        fetch(`/control/${eventType}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                songNumber: inputNumber,
                pitch: pitch
            })
        }).catch(err => console.error(`Failed to send ${eventType}:`, err));
    }

    /* 履歴管理 */
    function createHistoryRecord() {
        const createdAt = Math.floor(Date.now() / 1000);
        return fetch("/history/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                songNumber: inputNumber,
                pitch: pitch,
                created_at: createdAt
            })
        })
        .then(res => res.json())
        .then(data => {
            historyDocId = data.docId;
        })
        .catch(err => {
            console.error("履歴の新規作成エラー:", err);
        });
    }
    
    function updateHistory(status) {
        if (!historyDocId) {
            console.warn("historyDocId が未設定のため、履歴更新をスキップ");
            return;
        }

        const createdAt = Math.floor(Date.now() / 1000);
        const payload = {
            status: status,
            created_at: createdAt
        };

        if (status === "playStarted") {
            payload.pitch = pitch;  // pitchを追加
        }

        fetch(`/history/update/${historyDocId}`, {
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
            }, 5000);
        });
    }

    /* 選曲画面 */
    function resetToSelection() {
        inputBox.style.color = "white";
        initVariables();
        inputBox.innerHTML = initialHTML;
        scrollBg.style.display = "none";
        scrollingDiv.style.display = "none";
        setBackground("static/background/input_blank.png");
    }

    /* 選曲画面（休憩明け） */
    async function afterTimer() {
        video.style.display = "none";
        inputBox.style.color = "white";
        setBackground("static/background/input_blank.png");
        inputBox.innerHTML = "예약정보수신중...";
        sendPlaybackEvent("playEnded");
        initVariables();
    
        const next = await fetchNextReservedSong();
        if (next.has_next && next.song && next.song.songNumber) {
            inputNumber = next.song.songNumber;
            checkSong();
        } else {
            resetToSelection();
        }
    };

    /* 効果音再生 */
    function playSound(filename) {
        try {
            const sound = new Audio(`static/sounds/${filename}`);
            sound.play().catch(error => console.error("音声再生エラー:", error));
        } catch (error) {
            console.error("playSound() でエラー:", error);
        }
    }

    /* 秒数を分秒に */
    function formatSeconds(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        const formattedSeconds = remainingSeconds.toString().padStart(2, '0');
        return `${minutes}:${formattedSeconds}`;
    }

    /* 曲情報生成 */
    function getRemarks(songInfo) {
        let remarks_array = [];
        let lyricist = songInfo.lyricist || "";
        let composer = songInfo.composer || "";
        let lyricStart = highlightGreatLeaders(songInfo.lyricStart || "");
        console.log(songInfo);

        duration = formatSeconds(songInfo.duration);
    
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

        remarks = lyricStart
            ? `<span class='lyrics fade-in'>♫ ${lyricStart}</span><br><span class='remarks'>${remarks_array.join(" ")}</span>`
            : `<span class='remarks'>${remarks_array.join(" ")}</span>`;
    }

    /* 曲存在確認、再生準備画面 */
    function checkSong() {
        if (inputNumber.startsWith("98")) {
            const minutes = parseInt(inputNumber.slice(2), 10);
            if (!isNaN(minutes)) {
                startTimerWithBGM(minutes);
                return;
            }
        }

        fetch(`/song_info/${inputNumber}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.songName) {
                    songInfo = data;
                    getRemarks(songInfo);
                    createHistoryRecord().then(() => {
                        showPitchSelection();
                        playPreview(songNumber = inputNumber);
                    });
                } else {
                    inputNumber = "";
                    songInfo = {};
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
                bgmPlayer = new Audio(`/bgm/${fileList[currentIndex]}`);
                bgmPlayer.volume = 0.3;
                bgmPlayer.play();
                updateScrollingHistory();

                const playNext = () => {
                    currentIndex = (currentIndex + 1) % fileList.length;
                    bgmPlayer.src = `/bgm/${fileList[currentIndex]}`;
                    bgmPlayer.play();
                };

                bgmPlayer.addEventListener("ended", playNext);

                countdown = setInterval(() => {
                    remainingSeconds--;
                    inputBox.innerHTML = `<p class='song-name'>휴식시간</p><p class='large'>${Math.floor(remainingSeconds / 60)}:${(remainingSeconds % 60).toString().padStart(2, '0')}</p>`;
                    if (remainingSeconds <= 0) {
                        clearInterval(countdown);
                        countdown = null;
                        bgmPlayer.pause();
                        bgmPlayer = null;
                        inputBox.innerHTML = "<p>휴식시간이 다 됐습니다</p>";
                        setTimeout(afterTimer, 3000);
                    }
                }, 1000);
            });
    }

    /* 再生準備画面の文字情報 */
    function generateSongSelectedHTML() {
        const pitchDisplay = pitch > 0 ? `+${pitch}` : pitch.toString();
        return `<p>${inputNumber}</p><p class='song-name'>${highlightGreatLeaders(songInfo.songName)}</p><p>${remarks}</p><p>${duration} | 음정 ${pitchDisplay}</p>`;
    }

    /* 再生準備画面 */
    function showPitchSelection() {
        setBackground("static/background/input_blank.png");
        inputBox.innerHTML = generateSongSelectedHTML();
    }

    function stopPreview() {
        if (currentPreviewAudio) {
            currentPreviewAudio.pause();
            currentPreviewAudio.currentTime = 0;
            currentPreviewAudio = null;
        }
    }

    function playPreview(songNumber, pitch = 0, start = null, duration = 8) {
        if (currentPreviewAudio) {
            stopPreview();
        }

        const params = new URLSearchParams();
        params.set("pitch", pitch);
        if (start !== null) params.set("start", start);
        if (duration !== null) params.set("duration", duration);
    
        const previewAudio = new Audio(`/preview/${songNumber}?${params.toString()}`);
        previewAudio.volume = 0.5;
        previewAudio.play().catch(error => console.error("プレビュー音声再生エラー:", error));

        currentPreviewAudio = previewAudio;
    }

    /* 動画問い合わせ */
    function startConversion() {
        inputBox.innerHTML += "<p class='lyrics blink-fast' style='background:white;'>내리적재중...Downloading Video</p>"
        if (pitch != 0) {
            if (currentPreviewAudio) {
                stopPreview();
            };
            waitMusic = new Audio("static/sounds/wait2.mp3");
            waitMusic.play().catch(error => console.error("変換中音声再生エラー:", error));;
        };
        fetch("/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ song_number: inputNumber, pitch })
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
        if (currentPreviewAudio) {
            stopPreview();
        };
        if (waitMusic) {
            waitMusic.pause();
            waitMusic = null;
        };
    
        document.body.style.backgroundImage = "none";
        inputBox.innerHTML = "";
        inputBox.style.color = "transparent";
        video.src = filename;  // ← 署名付きURLをそのままセット！
        video.style.display = "block";

        video.play().then(() => {
            updateHistory("playStarted");
            video.onended = async () => {
                video.style.display = "none";
                inputBox.style.color = "white";
                setBackground("static/background/input_blank.png");
                inputBox.innerHTML = "예약정보수신중...";
                updateHistory("playFinished");
                initVariables();
    
                const next = await fetchNextReservedSong();
                if (next.has_next && next.song && next.song.songNumber) {
                    inputNumber = next.song.songNumber;
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
        document.getElementById('clock').textContent = `${latestEvent}${hours}:${minutes}:${seconds}`;
    }

    setInterval(updateClock, 1000);
    getEventInfo();
    updateClock();

    startButton.addEventListener("click", () => {
        startButton.style.display = "none";
        launchImg.style.display = "none";
        resetToStartup();
    });

    /* キーバインド */
    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {
            if (countdown !== null) {
                clearInterval(countdown);
                countdown = null;
            }
            if (bgmPlayer !== null) {
                bgmPlayer.pause();
                bgmPlayer = null;
            }

            if (!video.paused && video.currentTime > 0) {
                video.pause();
                updateHistory("playAborted");
            } else if (inputNumber.length === 4 && !video.src) {
                updateHistory("songCancelled");
            }
            
            stopPreview();
            video.currentTime = 0;
            video.style.display = "none";
            resetToSelection();
        }

        if (event.key >= "0" && event.key <= "9" && inputNumber.length < 4) {
            inputNumber += event.key;
            inputBox.innerHTML = `<p class='large'>${"____".slice(inputNumber.length) + inputNumber}</p>`;
            playSound(`${event.key}.mp3`);
            if (inputNumber.length === 4) {
                checkSong();
            }
        } else if (event.key === "+" && pitch < 8) {
            pitch++;
            inputBox.innerHTML = generateSongSelectedHTML();
            playSound(`plus.mp3`);
            playPreview(songNumber=inputNumber, pitch=pitch);
        } else if (event.key === "-" && pitch > -8) {
            pitch--;
            inputBox.innerHTML = generateSongSelectedHTML();
            playSound(`minus.mp3`);
            playPreview(songNumber=inputNumber, pitch=pitch);
        } else if (event.key === "Enter" && inputNumber.length === 4) {
            startConversion();
            playSound("enter.mp3");
        }
    });

    console.log("《발사준비 끝!》");
});

