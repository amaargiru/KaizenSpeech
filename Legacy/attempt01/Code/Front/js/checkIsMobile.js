const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

if (isMobile) {
    document.body.style.fontSize = "2.2vmax";
} else {
    document.body.style.fontSize = "1.2vmax";
}
