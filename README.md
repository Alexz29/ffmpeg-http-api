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

