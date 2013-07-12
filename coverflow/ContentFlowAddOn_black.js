/*  ContentFlowAddOn_black, version 2.0 
 *  (c) 2008 - 2010 Sebastian Kutsch
 *  <http://www.jacksasylum.eu/ContentFlow/>
 *
 *  This file is distributed under the terms of the MIT license.
 *  (see http://www.jacksasylum.eu/ContentFlow/LICENSE)
 */

new ContentFlowAddOn ('black', {
    
    init: function () {
        this.addStylesheet();
    },
	
	ContentFlowConf: {
        reflectionColor: "#000000" // none, transparent, overlay or hex RGB CSS style #RRGGBB
	}

});
