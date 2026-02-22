
document.addEventListener('DOMContentLoaded', function() {
    const timerElement = document.getElementById('countdown-timer');
    const tryAgainElement = document.getElementById('try-again-message');

    // 1. Leemos la duración desde el atributo 'data-duration' del HTML.
    let duration = parseInt(timerElement.getAttribute('data-duration'));

    const timer = setInterval(function () {
        let minutes = Math.floor(duration / 60);
        let seconds = duration % 60;

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        timerElement.textContent = minutes + ":" + seconds;

        if (--duration < 0) {
            clearInterval(timer);
            timerElement.style.display = 'none';
            tryAgainElement.style.display = 'block';
        }
    }, 1000);
});