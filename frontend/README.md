# MODiR Landscape Prototype using D3

**NOTE:** This is an older version. The demo is maintained at https://github.com/TimRepke/modir-viewer

run server:

```
python server.py
```

navigate browser to http://0.0.0.0:8000/vis/index_news.html

## File Format

* docs (dict, keys are str IDs)
  * id (str, same as key)
  * date (str, '2004-01-01T12:12:00Z')
  * text (str)
  * category_a (str)
  * category_b (str)
  * keywords (list of str)
  * vec (list of float len 2, xy coordinates)
  * nodes (list of str(int), see node IDs)
* nodes (dict), keys are str(int)
  * id (str, same as key)
  * name (str)
  * vec (list of float len 2, xy coordinates)
  * weight (int)
  * email (str)
  * org (str)
  * sent (list)
  * received (list)
  * docs (list of str, doc IDs)
  * categories_a (list of str)
  * categories_b (list of str)
* edges (list of dict)
  * source (str, node id)
  * target (str, node id)
  * source_pos (list of float len 2, xy coordinates)
  * target_pos (list of float len 2, xy coordinates)
  * weight (int)
  * docs (list of str (doc IDs))
* category_a_index (dict)
  * keys: category (str)
  * values (list of doc IDs)
* category_b_index (dict)
  * keys: category (str)
  * values (list of doc IDs)
* word_grid (list (tr) of lists (td) of lists [keyword (str), count (int)])
* size (dict)
  * minx (float)
  * maxx (float)
  * miny (float)
  * maxy (float)
  * width (float)
  * height (float)
  * node_weights (dict)
    * min (int)
    * max (int)
    * range (int)
  * edge_weights (dict)
    * min (int)
    * max (int)
    * range (int)
  * word_grid (dict)
    * cols (int)
    * rows (int)
    * cell_width (float)
    * cell_height (float)
  
