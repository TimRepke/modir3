d3.selection.prototype.moveToFront = function () {
    return this.each(function () {
        this.parentNode.appendChild(this);
    });
};

function pos_x(d) {
    return d['pos'][0];
}

function pos_y(d) {
    return d['pos'][1];
}

class Landscape {
    constructor(data) {

        this.data = data;
        this.size = data['size'];
        this.canvasSize = Landscape.computeSize();
        this.scale = [
            this.canvasSize[0] / this.size['width'],
            this.canvasSize[1] / this.size['height']];
        this.scaleData();


        this.svgContainer = this.initSVGContainer();
        this.svgGroup = this.svgContainer.append('g');
        this.heatmapGroup = this.svgGroup.append('g');
        this.edgeGroup = this.svgGroup.append('g');
        this.nodesGroup = this.svgGroup.append('g');
        this.wordGridGroup = this.svgGroup.append('g');
        this.documentGroup = this.svgGroup.append('g');

        let categoriesId = 'categories';
        let categoriesSearchId = 'categorySearch';
        let nodesId = 'persons';
        let nodesCheckboxId = 'nodes-checkbox';
        let edgesCheckboxId = 'connections-checkbox';
        let nodesSearchId = 'personSearch';
        let documentsId = 'filteredDocuments';
        let heatmapCheckboxId = 'heatmap-checkbox';
        this.documentGroup.attr('id', documentsId);

        this.categories = new Categories(data, categoriesSearchId, categoriesId, 'category_b', heatmapCheckboxId);
        this.edges = new Edges(data, this.edgeGroup, edgesCheckboxId);
        this.nodes = new Nodes(data, this.nodesGroup, nodesSearchId, nodesId, nodesCheckboxId);
        this.heatmap = new Heatmap(data, this.heatmapGroup, this.canvasSize, documentsId, heatmapCheckboxId);
        this.wordGrid = new WordGrid(data, this.wordGridGroup, this.scale);
        this.documents = new Documents(data, this.documentGroup, this.categories, categoriesId, nodesId, documentsId);

        this.update();
        this.initZoom();
        this.initSidebar();
    }

    update() {
        this.heatmap.update();
        this.documents.update();
        this.edges.update();
        this.nodes.update();
        this.categories.update();
        this.wordGrid.update();
    }

    initSVGContainer() {
        return d3.select("#graph").append("svg")
            .attr("width", this.canvasSize[0])
            .attr("height", this.canvasSize[1])
            .attr("id", "svg");
    }

    initSidebar() {
        let that = this;
        $("#slider-min-size").slider({
            slide: function (event, ui) {
                that.slideSize(ui.value / 10);
            },
            orientation: "horizontal",
            range: "min",
            min: 5,
            max: 30,
            value: 10,
            animate: true
        });
    }

    slideSize(scale) {
        this.nodes.customPointScale = scale;
        this.documents.customPointScale = scale;
        this.update();
    }

    static computeSize() {
        let main = $('#main');
        let navbar = $('#top-navbar');
        return [main.width(), main.height() - navbar.height()];
    }

    calculateVectorPosition(vec) {
        let x = (vec[0] + Math.abs(this.size['minx'])) * this.scale[0];
        let y = Math.abs(vec[1] - this.size['maxy']) * this.scale[1];
        return [x, y];
    }

    scaleData() {
        for (let key in this.data['docs']) {
            this.data['docs'][key]['pos'] = this.calculateVectorPosition(this.data['docs'][key]['vec']);
        }
        for (let key in this.data['nodes']) {
            this.data['nodes'][key]['pos'] = this.calculateVectorPosition(this.data['nodes'][key]['vec']);
        }
        for (let key in this.data['edges']) {
            this.data['edges'][key]['source_pos'] = this.calculateVectorPosition(this.data['edges'][key]['source_pos']);
            this.data['edges'][key]['target_pos'] = this.calculateVectorPosition(this.data['edges'][key]['target_pos']);
        }
    }

    initZoom() {
        let that = this;
        this.svgContainer.call(d3.zoom()
            .scaleExtent([1 / 4, 10])
            .on("zoom", function () {
                that.svgGroup.attr("transform", d3.event.transform);
                let currentZoomLevel = d3.event.transform.k;
                that.adjustZoomLevel(currentZoomLevel);
            }));
        this.adjustZoomLevel(1.0);
    }

    adjustZoomLevel(currentZoomLevel) {
        this.nodes.adjustZoomLevel(currentZoomLevel);
        this.wordGrid.adjustZoomLevel(currentZoomLevel);
        this.documents.adjustZoomLevel(currentZoomLevel);
    }


}
let landscapeInstance;
function init(data) {
    landscapeInstance = new Landscape(data);
}

d3.json(file, init);

function reload() {
    let elem = document.getElementById('svg');
    elem.parentNode.removeChild(elem);
    d3.json(file, init);
}

/*
let samplesize = {
    "minx": -0.8807507753,
    "maxx": 1.0,
    "miny": -0.7126128674,
    "maxy": 0.9409167171,
    "width": 1.8807507753,
    "height": 1.6535295844,
    "node_weights": {"min": 1, "max": 162, "range": 161},
    "edge_weights": {"min": 1, "max": 68, "range": 67},
    "word_grid": {"cols": 5, "rows": 5, "cell_width": 0.3761501551, "cell_height": 0.3307059169}
};
*/
