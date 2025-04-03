const initialHTML = "<span class='song-name blink'>노래를 선택합시다</span><br><span class='num'>____</span>"

document.addEventListener("DOMContentLoaded", () => {
    const audio = document.getElementById("audio");
    const inputBox = document.getElementById("input-box");
    const video = document.getElementById("video");
    const startButton = document.getElementById("start-button");

    let countdown = null;
    let bgmPlayer = null;
    let inputNumber = "";
    let songInfo = {};
    let remarks = "";
    let duration = "";
    let pitch = 0;

    function highlightGreatLeaders(text) {
        const names = ["김일성", "김정일", "김정은"];
        names.forEach(name => {
            const regex = new RegExp(name, "g");
            text = text.replace(regex, `<span class="great-leader">${name}</span>`);
        });
        return text;
    }

    function setBackground(image) {
        document.body.style.backgroundImage = `url(${image})`;
    }

    function initVariables() {
        inputNumber = "";
        songInfo = {};
        remarks = "";
        duration = "";
        pitch = 0;
    }

    function resetToStartup() {
        inputBox.style.color = "white";
        initVariables();
        inputBox.innerHTML = "";
        setBackground("static/background/title.png");
        audio.play();
        setTimeout(() => {
            setBackground("static/background/input_blank.png");
            inputBox.innerHTML = initialHTML;
        }, 5000);
    }

    function resetToSelection() {
        inputBox.style.color = "white";
        initVariables();
        inputBox.innerHTML = initialHTML;
        setBackground("static/background/input_blank.png");
    }

    function playSound(filename) {
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


    function getRemarks(songInfo) {
        let remarks_array = [];
        let lyricist = "";
        let composer = "";
        let lyricStart = "";
        console.log(songInfo);

        duration = formatSeconds(songInfo.duration);

        if (songInfo.lyricist) {
            lyricist = songInfo.lyricist;
        }
    
        if (songInfo.composer) {
            composer = songInfo.composer;
        }
    
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

        if (songInfo.lyricStart) {
            lyricStart = highlightGreatLeaders(songInfo.lyricStart)
        };
        if (lyricStart.length > 0) {
            remarks = `<span class='lyrics'>♫ ${lyricStart}</span><br><span class='remarks'>${remarks_array.join(" ")}</span>`
        } else {
            remarks = `<span class='remarks'>${remarks_array.join(" / ")}</span>`;
        };
    }

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
                if (JSON.stringify(data).length > 8) {
                    songInfo = data;
                    getRemarks(songInfo);
                    showPitchSelection();
                } else {
                    inputNumber = "";
                    songInfo = {};
                    inputBox.innerHTML = "<span class='num'>____</span>";
                }
            })
            .catch(error => console.error("曲リスト取得エラー:", error));
    }

    function startTimerWithBGM(minutes) {
        const totalSeconds = minutes * 60;
        let remainingSeconds = totalSeconds;

        inputBox.innerHTML = `<span class='song-name'>휴식시간</span><br>${minutes}분`;

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

                const playNext = () => {
                    currentIndex = (currentIndex + 1) % fileList.length;
                    bgmPlayer.src = `/bgm/${fileList[currentIndex]}`;
                    bgmPlayer.play();
                };

                bgmPlayer.addEventListener("ended", playNext);

                countdown = setInterval(() => {
                    remainingSeconds--;
                    inputBox.innerHTML = `<span class='song-name'>휴식시간</span><br>${Math.floor(remainingSeconds / 60)}:${(remainingSeconds % 60).toString().padStart(2, '0')}`;
                    if (remainingSeconds <= 0) {
                        clearInterval(countdown);
                        countdown = null;
                        bgmPlayer.pause();
                        bgmPlayer = null;
                        inputBox.innerHTML = "휴식시간이 다 됐습니다";
                        setTimeout(resetToSelection, 3000);
                    }
                }, 1000);
            });
    }

    function generateSongSelectedHTML() {
        return `<span class='num'>${inputNumber}</span><br><span class='song-name'>${highlightGreatLeaders(songInfo.songName)}</span><br>${remarks}<br>${duration} | 음정 <span class='num'>${pitch}</span>`;
    }

    function showPitchSelection() {
        setBackground("static/background/input_blank.png");
        inputBox.innerHTML = generateSongSelectedHTML();
    }

    function playChord(pitch, key) {
        if (!key) return;
    
        const noteMap = {
            "C": 1, "C#": 2, "Db": 2, "D": 3, "D#": 4, "Eb": 4,
            "E": 5, "F": 6, "F#": 7, "Gb": 7, "G": 8,
            "G#": 9, "Ab": 9, "A": 10, "A#": 11, "Bb": 11, "B": 12
        };
    
        // メジャー/マイナー判定
        const isMinor = key.endsWith("m");
        const baseNote = key.replace("m", "");
        let num = noteMap[baseNote];
    
        if (!num) return;
    
        let finalNote = num + pitch;
        while (finalNote < 1) finalNote += 12;
        while (finalNote > 12) finalNote -= 12;
    
        const fileNum = isMinor ? 20 + finalNote : finalNote;
        const chordFile = `chord/c_${fileNum.toString().padStart(2, "0")}.mp3`;
    
        playSound(chordFile);
    }

    function startConversion() {
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

    function playVideo(filename) {
        document.body.style.backgroundImage = "none";
        inputBox.style.color = "transparent";
        video.src = `/video/${filename}`;
        video.style.display = "block";
        video.play();
        video.onended = () => {
            video.style.display = "none";
            resetToSelection();
        };
    }

    function updateClock() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        document.getElementById('clock').textContent = `${hours}:${minutes}:${seconds}`;
    }

    setInterval(updateClock, 1000);
    updateClock();

    startButton.addEventListener("click", () => {
        startButton.style.display = "none";
        resetToStartup();
    });

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

            if (!video.paused) {
                video.pause();
            }
            video.currentTime = 0;
            video.style.display = "none";
            resetToSelection();
        }

        if (event.key >= "0" && event.key <= "9" && inputNumber.length < 4) {
            inputNumber += event.key;
            inputBox.innerHTML = `<span class='num'>${"____".slice(inputNumber.length) + inputNumber}</span>`;
            playSound(`${event.key}.mp3`);
            if (inputNumber.length === 4) {
                checkSong();
            }
        } else if (event.key === "+" && pitch < 8) {
            pitch++;
            inputBox.innerHTML = generateSongSelectedHTML();
            playChord(pitch, songInfo.songKey);
        } else if (event.key === "-" && pitch > -8) {
            pitch--;
            inputBox.innerHTML = generateSongSelectedHTML();
            playChord(pitch, songInfo.songKey);
        } else if (event.key === "Enter" && inputNumber.length === 4) {
            startConversion();
            playSound("enter.mp3");
        }
    });

    console.log("《발사준비 끝!》");
});

