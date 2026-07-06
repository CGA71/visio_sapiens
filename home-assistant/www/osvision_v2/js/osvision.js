console.log("OSVision V2");

class OSVision{

constructor(){

this.clock();

setInterval(()=>{

this.clock();

},1000);

}

clock(){

const d=new Date();

console.log(d.toLocaleTimeString());

}

}

window.osvision=new OSVision();