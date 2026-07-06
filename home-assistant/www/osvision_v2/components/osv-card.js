class OSVisionCard extends HTMLElement{

connectedCallback(){

this.innerHTML=`

<div class="osv-card">

<slot></slot>

</div>

`;

}

}

customElements.define("osv-card",OSVisionCard);