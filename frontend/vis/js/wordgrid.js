class WordGrid {
    constructor(data, wordGrid, scale) {
        this.data = data;
        this.wordGrid = wordGrid;
        this.scale = scale;
        this.zoom = 1.0;

        this.topWordsData = this.computeTopWordsData();
    }

    adjustZoomLevel(currentZoomLevel) {
        if (Math.abs(currentZoomLevel - this.zoom) > 0.1) {
            this.zoom = currentZoomLevel;
            this.update();
        }
    }

    update() {
        let wordsPerCell = this.topWordsData[0].length;
        let percentage = Math.max(Math.min(Math.pow(this.zoom, 2) / wordsPerCell, 1.0), 0.0);

        let data = this.topWordsData.reduce((acc, curr, i) => {
            let words = curr.slice(0, Math.ceil(percentage * curr.length));
            return acc.concat(words);
        }, []);

        let topWordsText = this.wordGrid.selectAll('text')
            .data(data);

        topWordsText
            .attr('x', this.xPosition.bind(this))
            .attr('y', this.yPosition.bind(this))
            .text(function (d) {
                return d['word'];
            })
            .attr("font-family", "sans-serif")
            .attr("font-size", this.fontSize.bind(this))
            .attr("fill", function (d) {
                return '#000000'
            })
            .attr("fill-opacity", this.fillOpacity.bind(this))
            .style('pointer-events', 'none');

        topWordsText
            .enter()
            .append('text')
            .attr('x', this.xPosition.bind(this))
            .attr('y', this.yPosition.bind(this))
            .text(function (d) {
                return d['word'];
            })
            .attr("font-family", "sans-serif")
            .attr("font-size", this.fontSize.bind(this))
            .attr("fill", function (d) {
                return '#000000'
            })
            .attr("fill-opacity", this.fillOpacity.bind(this))
            .style('pointer-events', 'none');

        topWordsText
            .exit()
            .remove();
    }

    xPosition(d) {
        return d.x;
    }

    yPosition(d) {
        return d.y;
    }

    fontSize(d) {
        let size = Math.max(Math.min(15 * (1 / this.zoom), 20), 8);
        size = Math.min(Math.max(size, d.size), 20);
        return size/this.zoom + 'px';
    }
    fillOpacity(d) {
        return 0.9;//return Math.max(Math.min(d.size / 5, 1.0), 0.4);
    }

    computeTopWordsData() {
        let gridSize = this.data['size']['word_grid'];
        let data = this.data['word_grid'].reduce((acc, curr, i) => {
            return acc.concat(curr);
        }, []);

        return data.reduce((acc, curr, i) => { // probably in row major order
            let row = Math.floor((i / gridSize['cols']));
            let col = Math.floor((i - (row * gridSize['rows'])) % gridSize['cols']);
            // console.log('col: ' + col + ' | row: ' + row);

            // current cell AABB
            let xmin = Math.ceil((col * gridSize['cell_width']) * this.scale[0]);
            let xmax = Math.ceil(((col + 1) * gridSize['cell_width']) * this.scale[0]);
            let ymin = Math.ceil((row * gridSize['cell_height']) * this.scale[1]);
            let ymax = Math.ceil(((row + 1) * gridSize['cell_height']) * this.scale[1]);

            let cell = [];
            for (let run = 0; run < 80 && run < curr.length; run++) {
                cell.push({
                    'x': Math.floor(Math.random() * (xmax - xmin + 1)) + xmin,
                    'y': Math.floor(Math.random() * (ymax - ymin + 1)) + ymin,
                    'size': curr[run][1],
                    'word': curr[run][0]
                });
            }
            if (cell.length > 0) {
                acc.push(cell);
            }

            return acc;
        }, []);
    }
}