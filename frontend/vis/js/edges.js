class Edges {
    constructor(data, svgGroup, checkboxId) {
        this.svgGroup = svgGroup;
        this.data = data;

        this.total = 100;
        this.thresholdLow = 0.0;
        this.thresholdHigh = 1.0;
        this.minWidth = 0.5;
        this.maxWidth = 20;
        this.minOpacity = 0.2;
        this.maxOpacity = 0.5;
        this.checkboxId = checkboxId;
        this.edgesVisible = true;

        this.edgesAll = this.data['edges'].sort(function(a,b){
            return a['weight']-b['weight'];
        });

        this.initLandscape();
        this.initSidebar();
    }

    initLandscape() {
        //this.update();
        // update is called on init in landscape
    }

    update() {
        let that = this;
        let edgesFiltered = this.edgesAll.filter(function (d, i) {
            return (that.edgesAll.length * that.thresholdLow) <= i &&
                i <= (that.edgesAll.length * that.thresholdHigh);
        });
        this.svgGroup.selectAll('line').remove();
        let edges = this.svgGroup.selectAll('line')
            .data(edgesFiltered)
            .enter()
            .append('line')
            .attr('x1', function (d) {
                return d['source_pos'][0];
            })
            .attr('y1', function (d) {
                return d['source_pos'][1];
            })
            .attr('x2', function (d) {
                return d['target_pos'][0];
            })
            .attr('y2', function (d) {
                return d['target_pos'][1];
            })
            .attr("stroke-width", function (d) {
                return that.minWidth + (that.maxWidth - that.minWidth) *
                    (d['weight'] / that.data['size']['edge_weights']['range']);
            })
            .attr("stroke-opacity", function (d) {
                return Math.min(
                    Math.max(1 - (d['weight'] / that.data['size']['edge_weights']['range']), that.minOpacity),
                    that.maxOpacity);
            })
            .attr("stroke", "black")
            .exit().remove();
    }

    initSidebar() {
        let that = this;
        $("#slider-connections").slider({
            range: true,
            min: 0,
            max: 100,
            slide: function (event, ui) {
                that.slideConnections(ui.values[0] / that.total, ui.values[1] / that.total);
            },
            step: 5,
            values: [0, 100],
            orientation: "horizontal",
            animate: true
        });
        $('#' + this.checkboxId).change(function() {
            that.edgesVisible = $(this).prop('checked');
            that.svgGroup.style('visibility', that.edgesVisible ? 'visible' : 'hidden' );
        })
    }

    slideConnections(percentageLow, percentageHigh) {
        this.thresholdLow = percentageLow;
        this.thresholdHigh = percentageHigh;
        this.update();
    }
}

/*
var sampleedges = [{
    "source": "1728478",
    "target": "1728478",
    "source_pos": [-0.8078079224, 0.735624373],
    "target_pos": [-0.8078079224, 0.735624373],
    "weight": 1,
    "docs": ["4d8d303fd622cf3bd0899bfe532fbee41202e718"]
}]
*/