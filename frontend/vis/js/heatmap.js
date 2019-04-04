class Heatmap {
    constructor(data, heatmap, canvasSize, documentsId, checkboxId) {
        this.data = data; // prob unused
        this.heatmap = heatmap;
        this.size = canvasSize;
        this.checkboxId = checkboxId;

        $('#' + documentsId).on('filteredDocuments', (event, documents) => { this.show(documents);});

        this.thresholdLow = 0.05;
        this.thresholdHigh = 1.0;
        this.total = 100;
        this.filteredDocuments = [];
        this.allDocuments = Object.values(this.data['docs']);

        this.heatmapOn = true;
        this.initSidebar();
    }


    computeGridResolution() { // todo compute smart scale which adjusts so the grid fits with error < epsilon or offset the heatmap??
        let scale = 20;
        let res = Math.max(Math.floor(this.size[0] / scale), Math.floor(this.size[1] / scale));
        return [res, res];
    }

    histSizeY() {
        return this.size[1] / this.computeGridResolution()[1];
    }

    histSizeX() {
        return this.size[0] / this.computeGridResolution()[0];
    }

    density(lst) {
        let grid = [];
        for (let i = 0; i < this.histSizeY(); i++) {
            grid[i] = [];
            for (let j = 0; j < this.histSizeX(); j++) {
                grid[i][j] = 0;
            }
        }

        lst.forEach((d) => {
            let x = (pos_x(d) / this.size[0]) * grid[0].length;
            let y = (pos_y(d) / this.size[1]) * grid.length;

            x = Math.max(Math.min(x, grid[0].length - 1), 0);
            y = Math.max(Math.min(y, grid.length - 1), 0);

            x = Math.floor(x);
            y = Math.floor(y);
            grid[y][x]++
        });

        return grid.reduce(function (acc, curr) {
            return acc.concat(curr);
        }, []);

    }

    show(documents) {
        this.filteredDocuments = documents;
        this.update();
    }

    update() {
        let docs = this.filteredDocuments.length === 0 ? this.allDocuments : this.filteredDocuments;

        if(!this.heatmapOn) {
            docs = [];
        }

        let hist = this.density(docs);

        /* .filter(function (d) {
        return d['from'] === highlight || d['to'] === highlight || highlight === 'none';
    })*/

        let min = Math.min.apply(Math, hist);
        let max = Math.max.apply(Math, hist);

        //var i0 = d3.interpolateHsvLong(d3.hsv(120, 1, 0.65), d3.hsv(60, 1, 0.90));
        //var i1 = d3.interpolateHsvLong(d3.hsv(60, 1, 0.90), d3.hsv(0, 0, 0.95));
        let i0 = d3.interpolateHsvLong(d3.hsv(95, 0.0, 1.0), d3.hsv(95, 1.0, 1.0)); // first white, second green
        let i1 = d3.interpolateHsvLong(d3.hsv(95, 1.0, 1.0), d3.hsv(95, 1.0, 0.5)); // first green, second dark green
        let that = this;
        let interpolateTerrain = function (t) {
            t = Math.min(1.0, Math.max(0.0, t));
            if (t < that.thresholdLow)
                return d3.hsv(1, 1, 1, 0); // red, invisible
            if (t > that.thresholdHigh)
                return d3.hsv(1, 0, 1, 1); // white, visible

            let s = (t - that.thresholdLow) / Math.abs(that.thresholdHigh - that.thresholdLow);
            if (s < 0.5) {
                return i0(s * 2);
            }
            else {
                return i1((s - 0.5) * 2);
            }
        };

        let color = d3.scaleSequential(interpolateTerrain).domain([min, max]);
        this.heatmap.selectAll('path').remove();
        this.heatmap.selectAll('path')
            .data(d3.contours()
                .smooth(true)
                .size([Math.ceil(that.histSizeX()), Math.ceil(that.histSizeY())])
                .thresholds(d3.range(min, max, 1))
                (hist))
            .enter().append("path")
            .attr("d", d3.geoPath(d3.geoIdentity().scale(this.computeGridResolution()[1]).translate([-8, -3])))
            .attr("fill", function (d) {
                return color(d.value);
            }).exit().remove();
    }

    resize(size) {
        this.size = size;
        this.update();
    }

    initSidebar() {
        let that = this;
        $("#slider-heatmap").slider({
            range: true,
            min: 0,
            max: that.total,
            slide: function (event, ui) {
                that.slideHeatmap(ui.values[0] / that.total, ui.values[1] / that.total);
            },
            step: 5,
            values: [5, 100],
            orientation: "horizontal",
            animate: true
        });
        $('#' + this.checkboxId).change(function() {
            that.heatmapOn = $(this).prop('checked');
            that.update();
        })
    }

    slideHeatmap(percentageLow, percentageHigh) {
        this.thresholdLow = percentageLow;
        this.thresholdHigh = percentageHigh;
        this.update();
    }

}