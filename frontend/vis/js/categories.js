class Categories {
    constructor(data, searchBoxId, listId, cat_type, heatmapCheckboxId) { // cat_type = category_a
        this.data = data;
        this.listId = listId;
        this.cat_type = cat_type;
        this.categories = data[cat_type + '_index'];
        this.searchBox = document.getElementById(searchBoxId);
        this.selectedCategory = null;
        this.heatmapCheckboxId = heatmapCheckboxId;

        let size = Object.keys(this.categories).length;
        let i = 0;
        for (let key in this.categories) {
            this.categories[key] = {
                'name' : key,
                'docs': this.categories[key],
                'colour': d3.hsv((i / size) * 360, 1, 0.7)
            };
            i++;
        }
        this.initSidebar();
        
    }

    getColour(doc) {
        let category = doc[this.cat_type];
        if (!category) return undefined;
        return this.categories[category]['colour'];
    }

    selectCategory(id) {
        this.selectedCategory = id;
        $('#' + this.heatmapCheckboxId).prop('checked', false).change();
        this.update();
    }

    isSelected(category) {
        return category['name'] === this.selectedCategory;
    }

    initSidebar() {
        let that = this;
        let categories = Object.values(that.categories).sort((a, b) => {return b['docs'].length - a['docs'].length;});

        this.radios = d3.select('#' + this.listId)
            .selectAll('div')
            .data(categories)
            .classed('funkyradio-primary', true)
            .enter()
            .append('div')
            .attr('category_name', function (d) {
                return d['name'] || 'none';
            });

        this.radios.insert('input')
            .attr('type', 'radio')
            .attr('name', 'radio')
            .attr('id', function (d, i) {
                return 'category_radio_' + i;
            })
            .attr('value', function (d) {
                return d['name'] || 'none';
            })
            .on('change', function () {
                that.selectCategory(this.value);
            });

        this.radios.insert('label')
            .attr('for', function (d, i) {
                return 'category_radio_' + i;
            })
            .classed('personLabel', true) //todo
            .text(function (d) {
                return (d['name'] || 'NONE!');
            })
            .on('change', function () {
                that.selectCategory(this.value);
            });

        this.searchBox.addEventListener('keyup', this.filterCategoryRadios.bind(this));
    }


    filterCategoryRadios() {

        let input = this.searchBox.value.toUpperCase();
        let divs = document.getElementById(this.listId).getElementsByTagName("div");

        for (let i = 0; i < divs.length; i++) {
            if (divs[i].getAttribute('category_name').toUpperCase().indexOf(input) > -1) {
                divs[i].style.display = "";
            } else {
                divs[i].style.display = "none";
            }
        }

    }


    getSelectedDocs() {
        return this.categories[this.selectedCategory] !== undefined ? this.categories[this.selectedCategory]['docs'] : [];
    }

    updateDocuments() {
        let selection = this.getSelectedDocs();
        $('#' + this.listId).trigger('selectedDocs', [selection]);
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
        this.updateDocuments();
    }
}

