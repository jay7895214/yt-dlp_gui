@ECHO OFF
set /p url="yt url: "
set /p section="section(*s-s): "

IF NOT "%section%"=="" (
yt-dlp.exe --ignore-config ^
--external-downloader aria2c --external-downloader-args aria2c:"--conf-path=aria2_yt-dlp.conf" ^
--youtube-skip-dash-manifest ^
--embed-metadata --no-part ^
--sub-lang zh-TW --write-sub --convert-subs srt ^
-P "D:/Download/yt-dlp" ^
-o "%%(uploader)s/%%(playlist)s_%%(upload_date)s_%%(title)s_%%(section_start)s-%%(section_end)s.%%(ext)s" ^
--download-sections "%section%" ^
"%url%"
) ELSE (
yt-dlp.exe --ignore-config ^
--external-downloader aria2c --external-downloader-args aria2c:"--conf-path=aria2_yt-dlp.conf" ^
--youtube-skip-dash-manifest ^
--embed-metadata --no-part ^
--sub-lang zh-TW --write-sub --convert-subs srt ^
-P "D:/Download/yt-dlp" ^
-o "%%(uploader)s/%%(playlist)s_%%(upload_date)s_%%(title)s.%%(ext)s" ^
"%url%"
)
PAUSE

::--external-downloader aria2c --external-downloader-args aria2c:"--conf-path=aria2_yt-dlp.conf" ^
::--external-downloader aria2c --external-downloader-args aria2c:"-j 16 --retry-wait 10 --max-tries 10" ^
::--merge-output-format mkv --prefer-free-formats ^
::--embed-thumbnail --convert-thumbnails jpg ^
