class Nodes {
    constructor(data, svgGroup, searchBoxId, listId, checkboxId) {
        this.data = data;
        this.svgGroup = svgGroup;
        this.searchBox = document.getElementById(searchBoxId);
        this.zoom = 1.0;
        this.customPointScale = 1.0;
        this.listId = listId;
        this.checkboxId = checkboxId;
        this.nodesVisible = true;

        this.nodeData = Object.values(this.data['nodes']).sort((a, b) => b['weight'] - a['weight'])

        //this.initLandscape();
        this.initSidebar();
        this.selectedNode = null;

        this.thresholdLow = 0;
        this.thresholdHigh = 100;
        this.total = 100;

        this.maxNodeWeight = this.nodeData.reduce((acc, curr, i) => {return Math.max(acc, curr['weight'])}, 0);

        this.update();
        this.adjustZoomLevel(1.0);

    }


    initSidebar() {
        let that = this;
        this.radios = d3.select('#' + this.listId)
            .selectAll('div')
            .data(['none'].concat(that.nodeData))
            .classed('funkyradio-primary', true)
            .enter()
            .append('div')
            .attr('node_name', function (d) {
                return d['name'] || 'none';
            });

        this.radios.insert('input')
            .attr('type', 'radio')
            .attr('name', 'radio')
            .attr('id', function (d, i) {
                return 'node_radio_' + i;
            })
            .attr('value', function (d) {
                return d['id'] || 'none';
            })
            .on('change', function () {
                that.selectNode(this.value);
            });

        this.radios.insert('label')
            .attr('for', function (d, i) {
                return 'node_radio_' + i;
            })
            .classed('personLabel', true) //todo
            .text(function (d) {
                return (d['name'] || 'NONE!') + ' (' + (d['weight'] || '*') + ')';
            })
            .on('change', function () {
                that.selectNode(this.value);
            });

        this.searchBox.addEventListener('keyup', this.filterNodeRadios.bind(this));


        $("#slider-nodes").slider({
            range: true,
            min: 0,
            max: 100,
            slide: function (event, ui) {
                that.slideNodes(ui.values[0] / that.total, ui.values[1] / that.total);
            },
            step: 5,
            values: [0, 100],
            orientation: "horizontal",
            animate: true
        });

        $('#' + this.checkboxId).change(function() {
            that.nodesVisible = $(this).prop('checked');
            that.svgGroup.style('visibility', that.nodesVisible ? 'visible' : 'hidden' );
        })
    }


    slideNodes(percentageLow, percentageHigh) {
        this.thresholdLow = percentageLow;
        this.thresholdHigh = percentageHigh;
        this.update();
    }

    adjustZoomLevel(currentZoomLevel) {
        let scale = Math.max(Math.min(1.5 / currentZoomLevel, 2.0), 1.0);
        if (Math.abs(scale - this.zoom) > 0.07) {
            this.zoom = scale;
            this.svgGroup.selectAll('circle').attr('r', this.zoomLevel.bind(this));
        }
    }

    zoomLevel(d) {
        let zoomLevel = 2 * this.zoom * this.customPointScale;
        if (this.isSelected(d)) return 3 * zoomLevel;
        return zoomLevel;
    }

    getSelectedNode() {
        return this.data['nodes'][this.selectedNode];
    }

    getSelectedDocs() {
        return this.getSelectedNode()['docs'];
    }

    filterNodeRadios() {

        let input = this.searchBox.value.toUpperCase();
        let divs = document.getElementById(this.listId).getElementsByTagName("div");

        for (let i = 0; i < divs.length; i++) {
            if (divs[i].getAttribute('node_name').toUpperCase().indexOf(input) > -1) {
                divs[i].style.display = "";
            } else {
                divs[i].style.display = "none";
            }
        }

    }

    dotClicked() {
        let domElement = $(event.target);
        //this.selectNode(domElement.attr('node_id'));
    }

    selectNode(id, update = true) {
        this.selectedNode = id;
        if (update) {
            this.update();
            let node = this.data['nodes'][this.selectedNode];
            let selection = node !== undefined ? node['docs'] : [];
            $('#' + this.listId).trigger('selectedDocs', [selection]);
        }

    }


    isSelected(node) {
        return node['id'] === this.selectedNode;
    }


    updateLandscape() {

        let that = this;

        let filteredNodeData = this.nodeData.slice(
            Math.max(Math.min(this.thresholdLow * this.nodeData.length, this.nodeData.length - 1), 0),
            Math.max(this.thresholdHigh * this.nodeData.length) - 1);
        filteredNodeData.reverse();

        let dots = this.svgGroup.selectAll("circle")
            .data(filteredNodeData);


        dots
            .attr('title', function (d) {
                return d['name'];
            })
            .attr('data-tooltip', 'tooltip')
            .attr('data-placement', 'top')
            .attr('data-html', 'true')
            .attr('node_id', function (d) {
                return d['id'];
            })
            .attr('name', function (d) {
                return d['name'];
            })
            .attr('onclick', this.dotClicked.bind(this))
            .attr("cx", pos_x)
            .attr("cy", pos_y);

        dots.enter()
            .append("circle")
            .attr('title', function (d) {
                return d['name'];
            })
            .attr('data-tooltip', 'tooltip')
            .attr('data-placement', 'top')
            .attr('data-html', 'true')
            .attr('node_id', function (d) {
                return d['id'];
            })
            .attr('name', function (d) {
                return d['name'];
            })
            .attr('onclick', this.dotClicked.bind(this))
            .attr("cx", pos_x)
            .attr("cy", pos_y);


        dots.exit().remove();

        let peopleCircleAttributes = dots
            .attr("r", (d) => {
                return this.zoomLevel(d);
            })
            .style("fill", function (d) {
                if (that.isSelected(d)) return '#ff0c27';
                return '#2357d6';
            })
            .style("fill-opacity", function (d) {
                if (that.isSelected(d)) return 1.0;
                return 0.8;
            })
            .style('stroke', function (d) {
                if (that.isSelected(d)) return 'white';
                return '';
            });

        let highlightedCircle = dots.filter(function (d) {
            return that.isSelected(d);
        }).moveToFront();
    }

    updateSidebar() {
        let that = this;
        this.radios
            .selectAll('div')
            .filter(function (d) {
                return that.isSelected(d);
            })
            .select('input')
            .attr('checked', 'true');
    }

    update() {
        this.updateSidebar();
        this.updateLandscape();
    }
}

/*
var example_node = {
    "1760871": {
        "id": "1760871",
        "name": "Aaron C. Courville",
        "vec": [-0.439512074, -0.4759511948],
        "weight": 74,
        "email": "",
        "org": "",
        "sent": [],
        "received": [],
        "docs": ["8c3679bab6b379a3f487c68f631f55bb18292bc0", "1e1e274d9dde08a5e6a02daf86405d1cee5ec5cd", "6701889c81ad460f53a4d84361cd3d37b4e02743", "83b625ae40c921c47255da5f2e24266e75a48d9b", "db8c3cfaae04a14c1209d62953029b6fa53e23c7", "2ae139b247057c02cda352f6661f46f7feb38e45", "534f6ea4ce0127e5da7f1cafb6334b59ad15b83f", "7e463877264e70d53c844cf4b1bf3b15baec8cfb", "013cd20c0eaffb9cab80875a43086e0c3224fe20", "12dd078034f72e4ebd9dfd9f80010d2ae7aaa337", "f9c431f58565f874f76a024add2aa80717ec5cf5", "517c31e5390d1d743aca69d16098be6ca30ebd2d", "00a10855b9ab0f2c04226b7a05a7371dea26090b", "2cb3bd0cff91c0afcbfb2cb10ce30313e0f70133", "16a333a43d587802f95b5ec11de6c99314ae0c77", "63cbac5a39cd926a806f60116b845f9bd70f5544", "5c0fe8ba39bda83d6ca3b9705a780809d52a67b4", "561008cb23d7a38a00806353ba3389c1b95395af", "60744af2f89291897839852d66582b1b2a0be0bc", "389bfe18dc161fda4980ec426ffaccec76a918bb", "069340a9fb06268b19e12a59de87547c9750fc79", "62c76ca0b2790c34e85ba1cce09d47be317c7235", "17f5c7411eeeeedf25b0db99a9130aa353aee4ba", "6de2b1058c5b717878cce4e7e50d3a372cc4aaa6", "0808bb50993547a533ea5254e0454024d98c5e2f", "78c91d969c55a4a61184f81001c376810cdbd541", "221cf7b15aa771f9f9f8c0dc21899e22cd736fb8", "01cbebbbcb973ae2d1d32a49fa1f1e0738153ba9", "2064c2a33eb0b4c8acd23fd60b98c12d6c1ad61e", "400f6f4304b1c12efb22acf7e80a1784015cb23a", "654a3e53fb41d8168798ee0ee61dfab73739b1ed", "2579b2066d0fcbeda5498f5053f201b10a8e254b", "46018a894d533813d67322827ca51f78aed6d59e", "6b570069f14c7588e066f7138e1f21af59d62e61", "18cc17c06e34baaa3e196db07e20facdbb17026d", "03f34688ef4ee4239464633784235387e9bff4bb", "8b358a216f83edb259decd68127722a356cc8adf", "3e4883a0ab6c5830785b83b5af74fcd63b1c556e", "73463ec3391df70d4c38de6a1e963830a85efbe6", "67bee729d046662c6ebd9d3d695823c9d820343a", "2b6a2adddfbf70ea5cb3d9d749c1ef70db8c230a", "b3610b7650533631ef7a63adf21ec0e722f4d9c0", "4f5d7dc3d41236ed6a42cf4105cc79fa2fb0828d", "6ca1898dac153b8cd500c0c2633675b05d3c638c", "36818eaf6376aeeaffed2523d28bebae7c9db8d7", "5796ba3a657261a49ca9333865b8606980111371", "046a1302079f56b94c81457bf7fd21c3417a9f72", "0406f0696982b26bdf2a456123439c8ddcf8afb1", "6a0e1ce1ea01eb5eccf7c852a26f0e3db85e856e", "5dc1fd136278c61771fbc43473c9e21638f0f46f", "0a82cb606e561ca6f43697ca4df4f449b82ddba6", "14d904e10cca3f0cb6d9c623db1a50152cec6360", "2b35a5bccb678532412bcb471c16d6208353cf62", "fd7447a976968cd4190c65edef8482f4f8e0cab9", "cf280435c471ee099148c4eb9eb2e106ccb2b218", "aeb38c8c4b826ad0dc63911dc5198f8c565298f5", "f8c8619ea7d68e604e40b814b40c72888a755e95", "78507d14c925e16d628bc643c75c449267fef64c", "8ec543a9e6b4ae5b3c9f6f938ae5a9bdf77d82ac", "5656fa5aa6e1beeb98703fc53ec112ad227c49ca", "2b329183e93cb8c1c20c911c765d9a94f34b5ed5", "41f50d08e4c237d0f192f5c09f78d7e1d09d9cef", "5e3b036c44f0c3b0b5eb1e99ef78644dcabcf2f0", "bbb6bef6b2e48f5088f9bc0fd7cf7c07d514ea2a", "e21a6a56e24f321286a50f2a1811ae66ef6245f2", "4a350352b2fb426530693d42f45effd049537cab", "146f6f6ed688c905fb6e346ad02332efd5464616", "6bf6a3fd2c4c17c4326b81424ce19aba0a4b9c42", "0a6193e3693356ae19c3ec3ed7c1375260a9e4a1", "0d24a0695c9fc669e643bad51d4e14f056329dec", "a4ab5ad02c4ed463e1e8a5c06e8b176ef3dea2ea", "7a7a2658df5d66541305962d4c9d43078adadac6", "524b24a3523123785bedccfa0ef6c4857bf21b5f", "18758118e78ca7f908021c55196fcba12dbb6283"],
        "categories_a": ["ArXiv", "ICML", "ArXiv", "NIPS", "ArXiv", "", "ArXiv", "ICML", "ArXiv", "Pattern Analysis and Machine Intelligence", "AAAI", "ICMI", "ICML", "ArXiv", "ArXiv", "ArXiv", "ArXiv", "NIPS", "ArXiv", "ArXiv", "AAAI", "ArXiv", "ArXiv", "ArXiv", "ICONIP", "NIPS", "ICML", "AISTATS", "ArXiv", "RecSys", "NIPS", "ArXiv", "ICML", "Pattern Analysis and Machine Intelligence", "ArXiv", "NIPS", "AAAI", "ArXiv", "ArXiv", "CVPR", "ArXiv", "ArXiv", "Journal of Computer Vision", "NIPS", "ArXiv", "Handbook on Neural Information Processing", "NIPS", "Multimedia", "ICML", "CVPR", "ArXiv", "ICML", "ArXiv", "AAAI", "ArXiv", "ACL", "Pattern Analysis and Machine Intelligence", "ArXiv", "NIPS", "ArXiv", "ArXiv", "ICML", "Medical Image Analysis", "AISTATS", "Journal of Machine Learning Research", "ArXiv", "ECCV", "Nature", "INTERSPEECH", "ICML", "AISTATS", "ArXiv", "Multimodal User Interfaces", "ICCV"],
        "categories_b": ["Journal", "ML", "Journal", "ML", "Journal", "Others", "Journal", "ML", "Journal", "Others", "AI", "Others", "ML", "Journal", "Journal", "Journal", "Journal", "ML", "Journal", "Journal", "AI", "Journal", "Journal", "Journal", "Others", "ML", "ML", "ML", "Journal", "Others", "ML", "Journal", "ML", "Others", "Journal", "ML", "AI", "Journal", "Journal", "ComVis", "Journal", "Journal", "Others", "ML", "Journal", "Others", "ML", "Others", "ML", "ComVis", "Journal", "ML", "Journal", "AI", "Journal", "ComLing", "Others", "Journal", "ML", "Journal", "Journal", "ML", "Others", "ML", "Others", "Journal", "ComVis", "Others", "Others", "ML", "ML", "Journal", "Others", "Others"]
    }
};
*/