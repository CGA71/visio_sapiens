class OSVisionCore extends HTMLElement{

connectedCallback(){

this.innerHTML=`

<div class="osv-core">

<div class="title">

OSVision V2

</div>

<div class="status">

NEURAL CORE ONLINE

</div>

</div>

`;

}

}

customElements.define("osv-core",OSVisionCore);