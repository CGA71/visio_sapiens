class OSVision{

constructor(){

this.version="2.0";

this.init();

}

init(){

console.log("OSVision V2");

this.startClock();

}

startClock(){

setInterval(()=>{

this.time=new Date();

},1000);

}

}

window.osvision=new OSVision();