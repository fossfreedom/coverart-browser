/*  ContentFlowAddOn_gallery2, version 1.0 
 *  (c) 2008 - 2010 Sebastian Kutsch
 *  <http://www.jacksasylum.eu/ContentFlow/>
 *
 *  This file is distributed under the terms of the MIT license.
 *  (see http://www.jacksasylum.eu/ContentFlow/LICENSE)
 */

new ContentFlowAddOn ('gallery2', {

    conf: {
        bigPicId: 'picframe',
        duration: 1000
    },

    init: function() {
        this.addStylesheet();
    },
    
    //onloadInit: function (flow) {
    afterContentFlowInit: function (flow) {
        var ac = flow.getAddOnConf("gallery2");
        var p = document.getElementById(ac.bigPicId);
        if (!p) {
            p = document.createElement('div')
            p.id = ac.bigPicId;
            flow.Container.parentNode.insertBefore(p, flow.Container);
        }
        p.style.textAlign = "center";
        $CF(window).addEvent('resize', function () {
            p.style.height = flow.maxHeight*1+"px";
            p.style.margin = flow.maxHeight/6 +"px auto";
        });
            
        var i = document.createElement('img');
        i.style.height = "100%";
        i.style.opacity = 0;
        i.style.filter = "alpha(opacity = 0 )";
        p.appendChild(i);

        flow.conf.onclickActiveItem(flow._activeItem);

    },

	
	ContentFlowConf: {
        scaleFactorLandscape: "max",     // scale factor of landscape images ('max' := height= maxItemHeight)
        scaleFactorPortrait: "max",
        fixItemSize: true,
        relativeItemPosition: "bottom center", // align top/above, bottom/below, left, right, center of position coordinate
        endOpacity: 0.3,                  // opacity of last visible item on both sides


        reflectionGap: 0.1,


        onclickInactiveItem : function (item) {
            this.conf.onclickActiveItem(item);
        },

        onclickActiveItem: function (item) {
            var ac = this.getAddOnConf("gallery2");
            var url, target;

            var d = ac.duration;
            opacity_delta = 0.02;
            timeout = opacity_delta * d;

            if (url = item.content.getAttribute('href')) { }
            else if (url = item.element.getAttribute('href')) { }
            else if (url = item.content.getAttribute('src')) { }

            var hideImage = function (img, src) {
                var o = img.style.opacity;
                o = parseFloat(o);
                if (o > 0 && img.src != "undefined" ) {
                    img.hide = true;
                    o = o - opacity_delta;
                    img.style.opacity = o;
                    img.style.filter = "alpha(opacity = "+o*100+")";
                    window.setTimeout( function () { hideImage(img, src) } , timeout);
                }
                else {
                    img.style.opacity = "0";
                    img.src = src;
                    img.hide = false;
                    showImage(img, src);
                }
            }

            var showImage = function (img, src) {
                var o = img.style.opacity;
                o = parseFloat(o);
                if (img.src.search(new RegExp(src)) < 0)  {
                    hideImage(img, src);
                }
                else if (o < 1 && !img.hide ) {
                    o = o + opacity_delta;
                    img.style.opacity = o;
                    img.style.filter = "alpha(opacity = "+o*100+")";
                    window.setTimeout( function () { showImage(img, src)} , timeout);
                }
            }

            if (url) {
                var pf = document.getElementById(ac.bigPicId).lastChild;
                showImage(pf, url);
            }
        },
        
        
        onReachTarget: function(item) {
            this.conf.onclickActiveItem(item);
        },

        /* ==================== calculations ==================== */

        

        calcSize: function (item) {
            var vI = this.conf.visibleItems;
            var x = 2/vI;
            return {width: x, height: x};
        },

        calcCoordinates: function (item) {
            var rP = item.relativePosition;
            var x = rP*item.size.width/2*1.1*this.conf.scaleFactor;
            var y = -1;

            return {x: x, y: y};
        },
        

        calcOpacity: function (item) {
            return  Math.abs(item.relativePosition) <= 0.5 ? (1 - item.relativePosition) : this.conf.endOpacity;
        }
	
    }

});
