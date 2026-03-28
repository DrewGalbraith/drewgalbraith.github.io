/*!
    Title: Dev Portfolio Template
    Version: 1.2.2
    Last Change: 03/25/2020
    Author: Ryan Fitzgerald
    Repo: https://github.com/RyanFitzgerald/devportfolio-template
    Issues: https://github.com/RyanFitzgerald/devportfolio-template/issues

    Description: This file contains all the scripts associated with the single-page
    portfolio website.
*/

(function($) {

    // Show current year
    $("#current-year").text(new Date().getFullYear());

    // Remove no-js class
    $('html').removeClass('no-js');

    function setupRotatingSubtitle(selector, options) {
        var $subtitle = $(selector);
        var subtitles = options || [];
        var subtitleIndex;

        if (!$subtitle.length || !subtitles.length) {
            return;
        }

        subtitleIndex = Math.floor(Math.random() * subtitles.length);
        $subtitle.text(subtitles[subtitleIndex]);

        if (subtitles.length > 1) {
            window.setInterval(function() {
                $subtitle.addClass('is-transitioning-out');

                window.setTimeout(function() {
                    subtitleIndex = (subtitleIndex + 1) % subtitles.length;
                    $subtitle
                        .removeClass('is-transitioning-out')
                        .addClass('is-transitioning-in')
                        .text(subtitles[subtitleIndex]);

                    window.requestAnimationFrame(function() {
                        $subtitle.removeClass('is-transitioning-in');
                    });
                }, 250);
            }, 4000);
        }
    }

    // Rotate hero subtitles with a short slide/fade transition.
    setupRotatingSubtitle('#hero-subtitle', [
        'Gradschool dropout',
        'Web Developer',
        'LLM Researcher',
        'Linguist',
        'Privacy Zealot',
        'Budding Sci-Fi Fan',
        'Board Game Lover'
    ]);

    setupRotatingSubtitle('#george-orzowell-subtitle', [
        '"The Count of Monte Crisco"',
        '"Pride and Prego-dice"',
        '"A Tale of Two Zitis"',
        '"Charlie and the Chili Factory"',
        '"The Handmaid’s Taleggio"',
        '"Fifty Shades of Gravy"',
        '"Jurrasic Pork"',
        '"The Taming of the Stew"',
        '"Antony and Cleopasta"',
        '"War and Peas"',
        `"Al Dente's Inferno"`,
        '"Count Drac-stew-la"'
    ]);

    // Animate to section when nav is clicked
    $('header a').click(function(e) {
        var heading = $(this).attr('href');

        // Treat page-to-page links as normal navigation.
        if ($(this).hasClass('no-scroll') || !heading || heading.charAt(0) !== '#') {
            return;
        }

        e.preventDefault();
        var $target = $(heading);
        if (!$target.length) {
            return;
        }
        var scrollDistance = $target.offset().top;

        $('html, body').animate({
            scrollTop: scrollDistance + 'px'
        }, Math.abs(window.pageYOffset - $target.offset().top) / 1);

        // Hide the menu once clicked if mobile
        if ($('header').hasClass('active')) {
            $('header, body').removeClass('active');
        }
    });

    // Scroll to top
    $('#to-top').click(function() {
        $('html, body').animate({
            scrollTop: 0
        }, 500);
    });

    // Scroll to first element
    $('#lead-down span').click(function() {
        var $next = $('#lead').next();
        if (!$next.length) {
            return;
        }
        var scrollDistance = $next.offset().top;
        $('html, body').animate({
            scrollTop: scrollDistance + 'px'
        }, 500);
    });

    // Create timeline
    $('#experience-timeline').each(function() {

        $this = $(this); // Store reference to this
        $userContent = $this.children('div'); // user content

        // Create each timeline block
        $userContent.each(function() {
            $(this).addClass('vtimeline-content').wrap('<div class="vtimeline-point"><div class="vtimeline-block"></div></div>');
        });

        // Add icons to each block
        $this.find('.vtimeline-point').each(function() {
            $(this).prepend('<div class="vtimeline-icon"><i class="fa fa-map-marker"></i></div>');
        });

        // Add dates to the timeline if exists
        $this.find('.vtimeline-content').each(function() {
            var date = $(this).data('date');
            if (date) { // Prepend if exists
                $(this).parent().prepend('<span class="vtimeline-date">'+date+'</span>');
            }
        });

    });

    // Open mobile menu
    $('#mobile-menu-open').click(function() {
        $('header, body').addClass('active');
    });

    // Close mobile menu
    $('#mobile-menu-close').click(function() {
        $('header, body').removeClass('active');
    });

    // Load additional projects
    $('#view-more-projects').click(function(e){
        e.preventDefault();
        $(this).fadeOut(300, function() {
            $('#more-projects').fadeIn(300);
        });
    });

    function createEnglishLetterCountMap() {
        var letterCounts = {};
        var alphabet = 'abcdefghijklmnopqrstuvwxyz';
        var index;

        for (index = 0; index < alphabet.length; index += 1) {
            letterCounts[alphabet.charAt(index)] = 0;
        }

        return letterCounts;
    }

    function countEnglishLetters(textContent) {
        var letterCounts = createEnglishLetterCountMap();
        var normalizedText = textContent.toLowerCase();
        var index;
        var currentCharacter;

        for (index = 0; index < normalizedText.length; index += 1) {
            currentCharacter = normalizedText.charAt(index);

            if (Object.prototype.hasOwnProperty.call(letterCounts, currentCharacter)) {
                letterCounts[currentCharacter] += 1;
            }
        }

        return letterCounts;
    }

    function sumLetterCounts(letterCounts) {
        return Object.keys(letterCounts).reduce(function(total, letter) {
            return total + letterCounts[letter];
        }, 0);
    }

    function countWords(textContent) {
        var trimmedText = String(textContent || '').trim();

        if (!trimmedText) {
            return 0;
        }

        return trimmedText.split(/\s+/).length;
    }

    function analyzePackRequirements(letterCounts, packCounts) {
        var maxRatio = 0;
        var breakdown = [];
        var totalLettersNeeded = 0;
        var lettersPerPack = 0;

        Object.keys(packCounts).forEach(function(letter) {
            var needed = letterCounts[letter] || 0;
            var perPack = packCounts[letter];
            var rawRatio = perPack > 0 ? needed / perPack : 0;
            var packsForLetter = needed > 0 ? Math.ceil(rawRatio) : 0;

            totalLettersNeeded += needed;
            lettersPerPack += perPack;

            if (rawRatio > maxRatio) {
                maxRatio = rawRatio;
            }

            breakdown.push({
                letter: letter,
                needed: needed,
                perPack: perPack,
                rawRatio: rawRatio,
                packsForLetter: packsForLetter
            });
        });

        var packsNeeded = Math.ceil(maxRatio);
        var totalLettersPurchased = packsNeeded * lettersPerPack;
        var wastedLetters = Math.max(0, totalLettersPurchased - totalLettersNeeded);
        var wastePercentage = totalLettersPurchased > 0 ? (wastedLetters / totalLettersPurchased) * 100 : 0;

        return {
            packsNeeded: packsNeeded,
            maxRatio: maxRatio,
            limitingLetters: breakdown.filter(function(item) {
                return item.needed > 0 && item.rawRatio === maxRatio;
            }),
            breakdown: breakdown,
            wastedLetters: wastedLetters,
            wastePercentage: wastePercentage
        };
    }

    function formatApproximateNumber(value) {
        if (value <= 0) {
            return '~0';
        }

        return '~' + (Math.round(value / 10) * 10).toLocaleString();
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function scaleNumericString(value, multiplier, fallbackUnit) {
        var match = String(value).trim().match(/^(-?\d+(?:\.\d+)?)\s*(.*)$/);
        var numericValue;
        var unit;
        var scaledValue;

        if (!match) {
            return String(0) + (fallbackUnit || '');
        }

        numericValue = parseFloat(match[1], 10);
        unit = match[2] || fallbackUnit || '';
        scaledValue = numericValue * multiplier;

        if (unit === '%') {
            return String(Math.round(scaledValue * 100) / 100).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1') + unit;
        }

        return String(Math.round(scaledValue * 100) / 100).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1') + unit;
    }

    function buildDisplayNutritionData(baseNutritionData, containerCount) {
        var sourceColumn = baseNutritionData.columns.perContainer;
        var scaledNutrients = {};

        Object.keys(sourceColumn.nutrients).forEach(function(key) {
            scaledNutrients[key] = {
                amount: scaleNumericString(sourceColumn.nutrients[key].amount, containerCount),
                dailyValue: sourceColumn.nutrients[key].dailyValue ? scaleNumericString(sourceColumn.nutrients[key].dailyValue, containerCount, '%') : ''
            };
        });

        return {
            title: baseNutritionData.title,
            servingsPerContainer: containerCount,
            servingSize: baseNutritionData.servingSize,
            columns: {
                perServing: {
                    label: sourceColumn.label,
                    calories: Math.round(sourceColumn.calories * containerCount * 100) / 100,
                    nutrients: scaledNutrients,
                    notes: sourceColumn.notes
                }
            },
            footnote: baseNutritionData.footnote
        };
    }

    function renderNutritionLabel(nutritionData) {
        var perServing = nutritionData.columns.perServing;
        var nutrients = perServing.nutrients;

        function amount(key) {
            return escapeHtml(nutrients[key].amount);
        }

        function dv(key) {
            return nutrients[key].dailyValue ? escapeHtml(nutrients[key].dailyValue) : '';
        }

        function dvMarkup(key) {
            var value = dv(key);
            return value ? '<span class="nutrition-label-dv">' + value + '</span>' : '';
        }

        return '' +
            '<div class="nutrition-label-inner">' +
                '<div class="nutrition-label-title">' + escapeHtml(nutritionData.title) + '</div>' +
                '<div class="nutrition-label-rule nutrition-label-rule-thin"></div>' +
                '<div class="nutrition-label-serving-count">' + escapeHtml(nutritionData.servingsPerContainer) + ' serving' + (nutritionData.servingsPerContainer === 1 ? '' : 's') + ' per container</div>' +
                '<div class="nutrition-label-serving-row">' +
                    '<span class="nutrition-label-serving-label">Serving size</span>' +
                    '<span class="nutrition-label-serving-value">' + escapeHtml(nutritionData.servingSize) + '</span>' +
                '</div>' +
                '<div class="nutrition-label-rule nutrition-label-rule-heavy"></div>' +
                '<div class="nutrition-label-amount">Amount Per Serving</div>' +
                '<div class="nutrition-label-calories-row">' +
                    '<span class="nutrition-label-calories-label">Calories</span>' +
                    '<span class="nutrition-label-calories-value">' + escapeHtml(perServing.calories) + '</span>' +
                '</div>' +
                '<div class="nutrition-label-rule nutrition-label-rule-heavy"></div>' +
                '<div class="nutrition-label-dv-header">% Daily Value*</div>' +
                '<div class="nutrition-label-row nutrition-label-row-bold">' +
                    '<span><strong>Total Fat</strong> ' + amount('totalFat') + '</span>' +
                    dvMarkup('totalFat') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-indent">' +
                    '<span>Saturated Fat ' + amount('saturatedFat') + '</span>' +
                    dvMarkup('saturatedFat') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-indent nutrition-label-row-italic">' +
                    '<span>Trans Fat ' + amount('transFat') + '</span>' +
                    dvMarkup('transFat') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-bold">' +
                    '<span><strong>Cholesterol</strong> ' + amount('cholesterol') + '</span>' +
                    dvMarkup('cholesterol') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-bold">' +
                    '<span><strong>Sodium</strong> ' + amount('sodium') + '</span>' +
                    dvMarkup('sodium') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-bold">' +
                    '<span><strong>Total Carbohydrate</strong> ' + amount('totalCarbohydrate') + '</span>' +
                    dvMarkup('totalCarbohydrate') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-indent">' +
                    '<span>Dietary Fiber ' + amount('dietaryFiber') + '</span>' +
                    dvMarkup('dietaryFiber') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-indent">' +
                    '<span>Total Sugars ' + amount('totalSugars') + '</span>' +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-indent-deep">' +
                    '<span>Includes ' + amount('addedSugars') + ' Added Sugars</span>' +
                    dvMarkup('addedSugars') +
                '</div>' +
                '<div class="nutrition-label-row nutrition-label-row-bold nutrition-label-row-protein">' +
                    '<span><strong>Protein</strong> ' + amount('protein') + '</span>' +
                '</div>' +
                '<div class="nutrition-label-rule nutrition-label-rule-heavy nutrition-label-rule-vitamins"></div>' +
                '<div class="nutrition-label-micronutrients">' +
                    '<div class="nutrition-label-row"><span>Vitamin D ' + amount('vitaminD') + '</span>' + dvMarkup('vitaminD') + '</div>' +
                    '<div class="nutrition-label-row"><span>Calcium ' + amount('calcium') + '</span>' + dvMarkup('calcium') + '</div>' +
                    '<div class="nutrition-label-row"><span>Iron ' + amount('iron') + '</span>' + dvMarkup('iron') + '</div>' +
                    '<div class="nutrition-label-row"><span>Potassium ' + amount('potassium') + '</span>' + dvMarkup('potassium') + '</div>' +
                '</div>' +
                '<div class="nutrition-label-rule nutrition-label-rule-heavy"></div>' +
                '<div class="nutrition-label-footnote">' + escapeHtml(nutritionData.footnote) + '</div>' +
            '</div>';
    }

    function renderLetterGrid(packAnalysis) {
        var output = '';

        packAnalysis.breakdown.forEach(function(item) {
            output += '<div class="tool-letter-cell">' +
                '<div class="tool-letter-heading">' +
                    '<span class="tool-letter-key">' + item.letter.toUpperCase() + '</span>' +
                    '<span class="tool-letter-pack-count">' + item.packsForLetter + ' pack' + (item.packsForLetter === 1 ? '' : 's') + '</span>' +
                '</div>' +
                '<dl class="tool-letter-metrics">' +
                    '<div><dt>Need</dt><dd>' + item.needed + '</dd></div>' +
                    '<div><dt>Per pack</dt><dd>' + item.perPack + '</dd></div>' +
                    '<div><dt>Ratio</dt><dd>' + item.rawRatio.toFixed(2) + 'x</dd></div>' +
                '</dl>' +
            '</div>';
        });

        return output;
    }

    function setAnalyzerStatus(message, isError) {
        var statusElement = document.getElementById('george-orzowell-status');

        if (!statusElement) {
            return;
        }

        statusElement.className = isError ? 'tool-status is-error' : 'tool-status is-success';
        statusElement.textContent = message;
    }

    function isPlainTextFile(file) {
        var lowerName = file && file.name ? file.name.toLowerCase() : '';
        return !!file && (file.type === 'text/plain' || /\.txt$/i.test(lowerName));
    }

    function isPdfFile(file) {
        var lowerName = file && file.name ? file.name.toLowerCase() : '';
        return !!file && (file.type === 'application/pdf' || /\.pdf$/i.test(lowerName));
    }

    function extractPdfText(file) {
        var pdfjs = window.pdfjsLib;

        if (!pdfjs) {
            return Promise.reject(new Error('PDF support is unavailable.'));
        }

        pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.624/build/pdf.worker.min.mjs';

        return file.arrayBuffer().then(function(buffer) {
            var loadingTask = pdfjs.getDocument({ data: buffer });

            return loadingTask.promise.then(function(pdfDocument) {
                var pagePromises = [];
                var pageNumber;

                for (pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
                    pagePromises.push(
                        pdfDocument.getPage(pageNumber).then(function(page) {
                            return page.getTextContent().then(function(textContent) {
                                return textContent.items.map(function(item) {
                                    return item.str;
                                }).join(' ');
                            });
                        })
                    );
                }

                return Promise.all(pagePromises).then(function(pageTexts) {
                    return pageTexts.join('\n');
                });
            });
        });
    }

    function exportNutritionLabelPdf(labelElement) {
        var html2canvasLib = window.html2canvas;
        var jsPdfNamespace = window.jspdf;
        var JsPdfConstructor = jsPdfNamespace && jsPdfNamespace.jsPDF;

        if (!labelElement || !html2canvasLib || !JsPdfConstructor) {
            return Promise.reject(new Error('PDF export is unavailable.'));
        }

        return html2canvasLib(labelElement, {
            backgroundColor: '#ffffff',
            scale: 2
        }).then(function(canvas) {
            var imageData = canvas.toDataURL('image/png');
            var pdfWidth = canvas.width * 0.75;
            var pdfHeight = canvas.height * 0.75;
            var pdfDocument = new JsPdfConstructor({
                orientation: pdfWidth > pdfHeight ? 'landscape' : 'portrait',
                unit: 'pt',
                format: [pdfWidth, pdfHeight]
            });

            pdfDocument.addImage(imageData, 'PNG', 0, 0, pdfWidth, pdfHeight);
            pdfDocument.save('nutrition-label.pdf');
        });
    }

    function setupTextAnalyzer() {
        var form = document.getElementById('george-orzowell-form');
        var fileInput = document.getElementById('text-file-input');
        var clearFileButton = document.getElementById('george-orzowell-clear-file');
        var manualInput = document.getElementById('george-orzowell-manual-input');
        var clearInputButton = document.getElementById('george-orzowell-clear-input');
        var downloadLabelButton = document.getElementById('download-label-pdf');
        var results = document.getElementById('george-orzowell-results');
        var fileName = document.getElementById('george-orzowell-file-name');
        var wordCount = document.getElementById('george-orzowell-word-count');
        var letterTotal = document.getElementById('george-orzowell-letter-total');
        var packCount = document.getElementById('george-orzowell-pack-count');
        var limitingLetters = document.getElementById('george-orzowell-limiting-letters');
        var lettersWasted = document.getElementById('george-orzowell-letters-wasted');
        var nutritionLabelPreview = document.getElementById('nutrition-label-preview');
        var jsonOutput = document.getElementById('george-orzowell-json');
        var letterGrid = document.getElementById('george-orzowell-grid');
        var magnetPack = window.MAGNET_LETTER_PACK;
        var nutritionData = window.CANNED_FOOD_NUTRITION;
        var zeroNutritionData;

        if (!form || !fileInput || !clearFileButton || !manualInput || !clearInputButton || !downloadLabelButton || !results || !fileName || !wordCount || !letterTotal || !packCount || !limitingLetters || !lettersWasted || !nutritionLabelPreview || !jsonOutput || !magnetPack || !magnetPack.counts || !nutritionData) {
            return;
        }

        zeroNutritionData = buildDisplayNutritionData(nutritionData, 0);
        nutritionLabelPreview.innerHTML = renderNutritionLabel(zeroNutritionData);

        function resetAnalysis() {
            fileName.textContent = '-';
            wordCount.textContent = '0';
            letterTotal.textContent = '0';
            packCount.textContent = '0';
            limitingLetters.textContent = '-';
            lettersWasted.textContent = '~0 (0%)';
            nutritionLabelPreview.innerHTML = renderNutritionLabel(zeroNutritionData);
            jsonOutput.textContent = '{}';
            if (letterGrid) {
                letterGrid.innerHTML = '';
            }
            results.hidden = true;
            setAnalyzerStatus('', false);
        }

        function syncFileClearButton() {
            clearFileButton.hidden = !(fileInput.files && fileInput.files.length);
        }

        syncFileClearButton();

        fileInput.addEventListener('change', function() {
            syncFileClearButton();
        });

        clearFileButton.addEventListener('click', function() {
            fileInput.value = '';
            syncFileClearButton();
            resetAnalysis();
            fileInput.focus();
        });

        clearInputButton.addEventListener('click', function() {
            manualInput.value = '';
            resetAnalysis();
            manualInput.focus();
        });

        downloadLabelButton.addEventListener('click', function() {
            setAnalyzerStatus('Preparing nutrition label PDF...', false);

            exportNutritionLabelPdf(nutritionLabelPreview).then(function() {
                setAnalyzerStatus('Nutrition label PDF downloaded.', false);
            }).catch(function() {
                setAnalyzerStatus('The nutrition label could not be exported right now.', true);
            });
        });

        function renderAnalysis(textContent, sourceLabel) {
            var letterCounts = countEnglishLetters(textContent);
            var packAnalysis = analyzePackRequirements(letterCounts, magnetPack.counts);
            var scaledNutritionData = buildDisplayNutritionData(nutritionData, packAnalysis.packsNeeded);

            fileName.textContent = sourceLabel;
            wordCount.textContent = countWords(textContent).toLocaleString();
            letterTotal.textContent = sumLetterCounts(letterCounts).toLocaleString();
            packCount.textContent = packAnalysis.packsNeeded.toLocaleString();
            limitingLetters.textContent = packAnalysis.limitingLetters.length ? packAnalysis.limitingLetters.map(function(item) {
                return item.letter.toUpperCase();
            }).join(', ') : 'None';
            lettersWasted.textContent = formatApproximateNumber(packAnalysis.wastedLetters) + ' (' + Math.round(packAnalysis.wastePercentage) + '%)';
            nutritionLabelPreview.innerHTML = renderNutritionLabel(scaledNutritionData);
            jsonOutput.textContent = JSON.stringify(letterCounts, null, 2);
            if (letterGrid) {
                letterGrid.innerHTML = renderLetterGrid(packAnalysis);
            }
            results.hidden = false;

            setAnalyzerStatus('Analysis complete! See stats below.', false);
        }

        form.addEventListener('submit', function(event) {
            var selectedFile = fileInput.files && fileInput.files[0];
            var manualText = manualInput.value;
            var hasManualText = manualText.trim().length > 0;

            event.preventDefault();
            results.hidden = true;

            if (!selectedFile && !hasManualText) {
                setAnalyzerStatus('Paste text or upload a file before analyzing!', true);
                return;
            }

            if (hasManualText) {
                setAnalyzerStatus('Analyzing pasted text in your browser...', false);
                renderAnalysis(manualText, 'Pasted text');
                return;
            }

            if (!isPlainTextFile(selectedFile) && !isPdfFile(selectedFile)) {
                setAnalyzerStatus('This tool currently accepts only `.txt` and text-based `.pdf` files.', true);
                return;
            }

            if (isPdfFile(selectedFile)) {
                setAnalyzerStatus('Extracting text from PDF in your browser...', false);

                extractPdfText(selectedFile).then(function(textContent) {
                    if (!textContent.trim()) {
                        setAnalyzerStatus('This PDF does not appear to contain extractable text. If it is scanned, try OCR first.', true);
                        return;
                    }

                    renderAnalysis(textContent, selectedFile.name);
                }).catch(function() {
                    setAnalyzerStatus('The PDF could not be read. Please try another PDF or upload a plain text file.', true);
                });
                return;
            }

            setAnalyzerStatus('Analyzing file in your browser...', false);

            selectedFile.text().then(function(textContent) {
                renderAnalysis(textContent, selectedFile.name);
            }).catch(function() {
                setAnalyzerStatus('The file could not be read. Please try another text file.', true);
            });
        });
    }

    setupTextAnalyzer();

})(jQuery);
