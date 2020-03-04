# Deploy to production

```
docker build .

docker images

//tag to gpu versin
docker tag {hash}  alexz291/ffmpeg-rest-api:gpu

docker push alexz291/ffmpeg-rest-api:gpu
```



#FFmpeg HTTP API for youtube


Docker run

```
docker build .
docker images
docker run -d -p 8002:8002 174051b6a313
```


###Example:

Start stream to youtube


```
http://localhost:8002/start?file=2.mp4&key= {your youtube broadcast key} &loop=11&delay=120

GET params
file - path to file
key - youtube key for broadcast
loop - how many time to run video 
delay - delay to run stream (sec)
```

Stop stream 
```
http://localhost:8002/stop?file=1.mp4&key= {your youtube broadcast key} &loop=11
```

Restart stream (start from stop timecode)
```
http://localhost:8002/restart?file=1.mp4&key= {your youtube broadcast key} &loop=11
```

To get stream status
```
http://localhost:8002/stream?key= {your youtube broadcast key} 
```






BITRATE="2500k" # Bitrate of the output video
FPS="30" # FPS video output
QUAL="medium" # FFMPEG quality preset
YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2" # Youtube RTMP base URL
IMAGE="some_picture_path.jpg" #Picture
SOURCE="http://64.71.79.181:5234/stream" # Radio Station
KEY="your_strean_key" # Stream name/key
SIZE="1920x1080"
FRAMERATE="2"

    ffmpeg -re -loop 1 \
    	-framerate "$FRAMERATE" \
    	-i "$IMAGE" \
    	-i "$SOURCE" \
    	-c:a aac \
    	-s "$SIZE" \
    	-ab 128k \
    	-b:v "$BITRATE" \
    	-threads 6 \
    	-qscale 3 \
    	-preset veryfast \
    	-vcodec libx264 \
    	-pix_fmt yuv420p \
    	-maxrate 2048k \
    	-bufsize 2048k \
    	-framerate 30 \
    	-g 2 \
    	-strict experimental \
    	-f flv \
    	"$YOUTUBE_URL/$KEY"
