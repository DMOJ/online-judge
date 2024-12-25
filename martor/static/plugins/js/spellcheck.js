/*
This code was adapted from the following project:

https://github.com/swenson/ace_spell_check_js
Copyright (c) 2013 Christopher Swenson

Code licensed under the MIT Public License:

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

 */

// You also need to load in typo.js and jquery.js

// You should configure these classes.
var lang = "en_US";
var dicPath = "/static/dicts/en_US.dic";
var affPath = "/static/dicts/en_US.aff";

// Make red underline for gutter and words.
$("<style type='text/css'>.ace_marker-layer .misspelled { position: absolute; z-index: -2; border-bottom: 1px solid red; margin-bottom: -1px; }</style>").appendTo("head");
$("<style type='text/css'>.misspelled { border-bottom: 1px solid red; margin-bottom: -1px; }</style>").appendTo("head");

// Load the dictionary.
// We have to load the dictionary files sequentially to ensure
var dictionary = null;
$.get(dicPath, function(data) {
	dicData = data;
}).done(function() {
  $.get(affPath, function(data) {
	  affData = data;
  }).done(function() {
  	console.log("Dictionary loaded");
    dictionary = new Typo(lang, affData, dicData);
  });
});

// Check the spelling of a line, and return [start, end]-pairs for misspelled words.
function misspelled(line) {
	var words = line.split(/[^a-zA-Z\-']/);
	var i = 0;
	var bads = [];
	for (word in words) {
		var x = words[word] + "";
		var checkWord = x.replace(/[^a-zA-Z\-']/g, '');
	  if (!dictionary.check(checkWord)) {
	    bads[bads.length] = [i, i + words[word].length];
	  }
	  i += words[word].length + 1;
  }
  return bads;
}

// Spell check the Ace editor contents.
function spell_check(editorID) {
  var editor = ace.edit(editorID);

  // Wait for the dictionary to be loaded.
  if (dictionary == null) {
    return;
  }

  if (editor.currently_spellchecking) {
  	return;
  }

  if (!editor.contents_modified) {
  	return;
  }
  editor.currently_spellchecking = true;
  var session = editor.getSession();

	// Clear all markers and gutter
	clear_spellcheck_markers(editorID);
	// Populate with markers and gutter
  try {
	  var Range = ace.require('ace/range').Range
	  var lines = session.getDocument().getAllLines();
	  for (var i in lines) {
	    // Check spelling of this line.
	    var misspellings = misspelled(lines[i]);

	    // Add markers and gutter markings.
	    if (misspellings.length > 0) {
	      session.addGutterDecoration(i, "misspelled");
		}

	    for (var j in misspellings) {
	      var range = new Range(i, misspellings[j][0], i, misspellings[j][1]);
	      editor.markers_present[editor.markers_present.length] = session.addMarker(range, "misspelled", "typo", true);
	    }
	  }
	} finally {
		editor.currently_spellchecking = false;
		editor.contents_modified = false;
	}
}

function enable_spellcheck(editorID) {
	var editor = ace.edit(editorID);
	editor.markers_present = [];
	editor.spellcheckEnabled = true;
	editor.currently_spellchecking = false;
	editor.contents_modified = true;

	ace.edit(editor).getSession().on('change', function(e) {
		if (editor.spellcheckEnabled) {
			editor.contents_modified = true;
			spell_check(editorID);
		};
	})
	// needed to trigger update once without input
	editor.contents_modified = true;
	spell_check(editorID);
}

function disable_spellcheck(editorID) {
	var editor = ace.edit(editorID);
	editor.spellcheckEnabled = false

	// Clear the markers
	clear_spellcheck_markers(editorID);
}

function clear_spellcheck_markers(editorID) {
	var editor = ace.edit(editorID);
	var session = editor.getSession();

	for (var i in editor.markers_present) {
		session.removeMarker(editor.markers_present[i]);
	};

	editor.markers_present = [];

	// Clear the gutter
	var lines = session.getDocument().getAllLines();
	for (var i in lines) {
		session.removeGutterDecoration(i, "misspelled");
	};
}
