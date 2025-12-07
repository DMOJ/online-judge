(function () {
    function getDocHeight() {
        var D = document;
        return Math.max(
            Math.max(D.body.scrollHeight, D.documentElement.scrollHeight),
            Math.max(D.body.offsetHeight, D.documentElement.offsetHeight),
            Math.max(D.body.clientHeight, D.documentElement.clientHeight)
        );
    }

    function getDocWidth() {
        var D = document;
        return Math.max(
            Math.max(D.body.scrollWidth, D.documentElement.scrollWidth),
            Math.max(D.body.offsetWidth, D.documentElement.offsetWidth),
            Math.max(D.body.clientWidth, D.documentElement.clientWidth)
        );
    }

    function next(elem) {
        // Credit to John Resig for this function
        // taken from Pro JavaScript techniques
        do {
            elem = elem.nextSibling;
        } while (elem && elem.nodeType != 1);
        return elem;
    }

    function prev(elem) {
        // Credit to John Resig for this function
        // taken from Pro JavaScript techniques
        do {
            elem = elem.previousSibling;
        } while (elem && elem.nodeType != 1);
        return elem;
    }

    function redraw(element) {
        element = $(element);
        var n = document.createTextNode(' ');
        element.appendChild(n);
        (function () {
            n.parentNode.removeChild(n)
        }).defer();
        return element;
    }

    function minimizeMaximize(widget, main_block, editor) {
        // Move the fullscreen container to <body> to escape any stacking contexts
        // created by ancestors (e.g., sticky/transform) and ensure it overlays header/footer.
        if (window.fullscreen === true) {
            // Exit fullscreen
            main_block.className = 'django-ace-editor';

            // Restore dimensions
            if (window.ace_widget) {
                widget.style.width = window.ace_widget.width + 'px';
                widget.style.height = window.ace_widget.height + 'px';
            }

            // Restore element to its original place in DOM
            if (main_block.__ace_placeholder && main_block.__ace_return_parent) {
                try {
                    main_block.__ace_return_parent.insertBefore(main_block, main_block.__ace_placeholder);
                    main_block.__ace_placeholder.parentNode && main_block.__ace_placeholder.parentNode.removeChild(main_block.__ace_placeholder);
                } catch (e) {
                    // no-op; best effort to restore
                }
            }
            main_block.__ace_placeholder = null;
            main_block.__ace_return_parent = null;

            // Clear any inline fullscreen styles
            try {
                main_block.style.position = '';
                main_block.style.top = '';
                main_block.style.left = '';
                main_block.style.right = '';
                main_block.style.bottom = '';
                main_block.style.zIndex = '';
            } catch (e) {}

            window.fullscreen = false;
        } else {
            // Enter fullscreen
            window.ace_widget = {
                'width': widget.offsetWidth,
                'height': widget.offsetHeight
            };

            // Insert a placeholder to remember original position
            var placeholder = document.createElement('span');
            placeholder.style.display = 'none';
            main_block.parentNode.insertBefore(placeholder, main_block);
            main_block.__ace_placeholder = placeholder;
            main_block.__ace_return_parent = placeholder.parentNode;

            // Move the block to body and apply fullscreen class
            document.body.appendChild(main_block);
            main_block.className = 'django-ace-editor-fullscreen';

            // Explicitly set inline styles to avoid stacking quirks in Edge/Windows
            // Ensures the editor overlays nav/footer/MathJax regardless of external CSS.
            try {
                main_block.style.position = 'fixed';
                main_block.style.top = '0';
                main_block.style.left = '0';
                main_block.style.right = '0';
                main_block.style.bottom = '0';
                main_block.style.zIndex = '2147483000';
            } catch (e) {}

            // Size to viewport
            widget.style.height = getDocHeight() - 30 + 'px';
            widget.style.width = getDocWidth() + 'px';

            window.scrollTo(0, 0);
            window.fullscreen = true;
        }
        editor.resize();
    }

    function apply_widget(widget) {
        var div = widget.firstChild,
            textarea = next(widget),
            editor = ace.edit(div),
            mode = widget.getAttribute('data-mode'),
            theme = widget.getAttribute('data-theme'),
            default_light_theme = widget.getAttribute('data-default-light-theme'),
            default_dark_theme = widget.getAttribute('data-default-dark-theme'),
            wordwrap = widget.getAttribute('data-wordwrap'),
            toolbar = prev(widget),
            main_block = toolbar.parentNode;

        // Toolbar maximize/minimize button
        var min_max = toolbar.getElementsByClassName('django-ace-max_min');
        min_max[0].onclick = function () {
            minimizeMaximize(widget, main_block, editor);
            return false;
        };

        editor.getSession().setValue(textarea.value);

        // the editor is initially absolute positioned
        textarea.style.display = "none";

        // options
        if (mode) {
            editor.getSession().setMode('ace/mode/' + mode);
        }
        if (theme) {
            editor.setTheme("ace/theme/" + theme);
        } else {
            if (window.matchMedia) {
                const setEditorTheme = function (is_dark) {
                    if (is_dark) {
                        editor.setTheme("ace/theme/" + default_dark_theme);
                    } else {
                        editor.setTheme("ace/theme/" + default_light_theme);
                    }
                }

                setEditorTheme(window.matchMedia('(prefers-color-scheme: dark)').matches);
                try {
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(ev) {
                        setEditorTheme(ev.matches);
                    })
                } catch (err) {
                    window.matchMedia('(prefers-color-scheme: dark)').addListener(function(ev) {
                        setEditorTheme(ev.matches);
                    })
                }
            }
        }
        if (wordwrap == "true") {
            editor.getSession().setUseWrapMode(true);
        }

        editor.getSession().on('change', function () {
            textarea.value = editor.getSession().getValue();
        });

        editor.commands.addCommands([
            {
                name: 'Full screen',
                bindKey: {win: 'Ctrl-F11', mac: 'Command-F11'},
                exec: function (editor) {
                    minimizeMaximize(widget, main_block, editor);
                },
                readOnly: true // false if this command should not apply in readOnly mode
            },
            {
                name: 'submit',
                bindKey: {win: 'Ctrl+Enter', mac: 'Command+Enter'},
                exec: function (editor) {
                    $('form#problem_submit').submit();
                },
                readOnly: true
            },
            {
                name: "showKeyboardShortcuts",
                bindKey: {win: "Ctrl-Shift-/", mac: "Command-Shift-/"},
                exec: function (editor) {
                    ace.config.loadModule("ace/ext/keybinding_menu", function (module) {
                        module.init(editor);
                        editor.showKeyboardShortcuts();
                    });
                }
            },
            {
                name: "increaseFontSize",
                bindKey: "Ctrl-+",
                exec: function (editor) {
                    var size = parseInt(editor.getFontSize(), 10) || 12;
                    editor.setFontSize(size + 1);
                }
            },
            {
                name: "decreaseFontSize",
                bindKey: "Ctrl+-",
                exec: function (editor) {
                    var size = parseInt(editor.getFontSize(), 10) || 12;
                    editor.setFontSize(Math.max(size - 1 || 1));
                }
            },
            {
                name: "resetFontSize",
                bindKey: "Ctrl+0",
                exec: function (editor) {
                    editor.setFontSize(12);
                }
            }
        ]);

        window[widget.id] = editor;
        $(widget).trigger('ace_load', [editor]);
    }

    function init() {
        var widgets = document.getElementsByClassName('django-ace-widget');

        for (var i = 0; i < widgets.length; i++) {
            var widget = widgets[i];
            widget.className = "django-ace-widget"; // remove `loading` class

            apply_widget(widget);
        }
    }

    if (window.addEventListener) { // W3C
        window.addEventListener('load', init);
    } else if (window.attachEvent) { // Microsoft
        window.attachEvent('onload', init);
    }
})();
