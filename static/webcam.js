var video = document.querySelector("#videoElement");
var stopVideo = document.querySelector(".WAIT");

function sleep(duration) {
	return new Promise(resolve => {
		setTimeout(() => {
			resolve()
		}, duration * 1000)
	})
}
        
        if (navigator.mediaDevices.getUserMedia) {
          navigator.mediaDevices.getUserMedia({ video: true })
            .then(function (stream) {
              video.srcObject = stream;
            })
            .catch(function (err0r) {
              console.log("Something went wrong!");
            });
        }

        stopVideo.addEventListener("click", stop, false);

        function stop(e) {
          //await sleep(10)
          var stream = video.srcObject;
          var tracks = stream.getTracks();
          for (var i = 0; i < tracks.length; i++) {
            var track = tracks[i];
            track.stop();
          }
    
          video.srcObject = null;
        }