/*  ContentFlowAddOn_vertical, version 2.0 
 *  (c) 2008 - 2010 Sebastian Kutsch
 *  <http://www.jacksasylum.eu/ContentFlow/>
 *
 *  This file is distributed under the terms of the MIT license.
 *  (see http://www.jacksasylum.eu/ContentFlow/LICENSE)
 */


new ContentFlowAddOn ('vertical', {

	ContentFlowConf: {
        relativeItemPosition: "center",         // top, bottom, left, right, center
        verticalFlow: true,            // turn ContentFlow 90 degree counterclockwise
        reflectionHeight: 0,

        calcCoordinates: function (item) {
            var rP = item.relativePosition;
            var rPN = item.relativePositionNormed;
            var vI = rPN != 0 ? rP/rPN : 0 ; // visible Items

            var f = 1 - 1/Math.exp( Math.abs(rP)*0.75);
            var x =  item.side * vI/(vI+1)* f; 
            var y = 0;

            return {x: x, y: y};
        }
	
    }

});
