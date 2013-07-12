/*  ContentFlowAddOn_roundabout, version 3.0 
 *  (c) 2008 - 2010 Sebastian Kutsch
 *  <http://www.jacksasylum.eu/ContentFlow/>
 *
 *  This file is distributed under the terms of the MIT license.
 *  (see http://www.jacksasylum.eu/ContentFlow/LICENSE)
 */

new ContentFlowAddOn ('roundabout', {

	ContentFlowConf: {
        circularFlow: true,
        visibleItems: -1,
        relativeItemPosition: "top center",
        endOpacity: 0.5,
	
        /*
         * calculates the size of the item at its relative position x
         * returns a size object
         */
        calcSize: function (item) {
            var rP = item.relativePosition;
            //var rPN = relativePositionNormed;
            //var vI = rPN != 0 ? rP/rPN : 0 ; // visible Items

            var h = 1/(Math.abs(rP)+1);
            var w = h;
            return {width: w, height: h};
        },

        /*
         * calculates the position of an item within the flow element
         * returns a vector object
         */
        calcCoordinates: function (item) {
            var rP = item.relativePosition;
            var rPN = item.relativePositionNormed;
            var vI = rPN != 0 ? rP/rPN : 0 ; // visible Items

            var f = 1 - 1/Math.exp( Math.abs(rP)*0.75);
            var x =  item.side * vI/(vI+1)* f; 
            var y = 1;

            var f = Math.sin(Math.PI * (rP*(1+1/(rP*rP+1))) / (vI+1));
            var x = vI/(vI+1)* f; 
            var y = 1 - Math.abs(rP)*1.5/(vI+1); 

            return {x: x, y: y};
        }

    }
});
