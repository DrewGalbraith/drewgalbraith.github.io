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

    // Rotate hero subtitles on the homepage with a short slide/fade transition.
    var heroSubtitles = [
        'Gradschool dropout',
        'Web Developer',
        'LLM Researcher',
        'Linguist',
        'Privacy Zealot',
        'Budding Sci-Fi Fan',
        'Board Game Lover',
    ];
    var $heroSubtitle = $('#hero-subtitle');
    if ($heroSubtitle.length) {
        var subtitleIndex = Math.floor(Math.random() * heroSubtitles.length);
        $heroSubtitle.text(heroSubtitles[subtitleIndex]);

        if (heroSubtitles.length > 1) {
            window.setInterval(function() {
                $heroSubtitle.addClass('is-transitioning-out');

                window.setTimeout(function() {
                    subtitleIndex = (subtitleIndex + 1) % heroSubtitles.length;
                    $heroSubtitle
                        .removeClass('is-transitioning-out')
                        .addClass('is-transitioning-in')
                        .text(heroSubtitles[subtitleIndex]);

                    window.requestAnimationFrame(function() {
                        $heroSubtitle.removeClass('is-transitioning-in');
                    });
                }, 250);
            }, 4000);
        }
    }

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

    function analyzePackRequirements(letterCounts, packCounts) {
        var maxRatio = 0;
        var breakdown = [];

        Object.keys(packCounts).forEach(function(letter) {
            var needed = letterCounts[letter] || 0;
            var perPack = packCounts[letter];
            var rawRatio = perPack > 0 ? needed / perPack : 0;
            var packsForLetter = needed > 0 ? Math.ceil(rawRatio) : 0;

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

        return {
            packsNeeded: Math.ceil(maxRatio),
            maxRatio: maxRatio,
            limitingLetters: breakdown.filter(function(item) {
                return item.needed > 0 && item.rawRatio === maxRatio;
            }),
            breakdown: breakdown
        };
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
        var statusElement = document.getElementById('text-analyzer-status');

        if (!statusElement) {
            return;
        }

        statusElement.className = isError ? 'tool-status is-error' : 'tool-status is-success';
        statusElement.textContent = message;
    }

    function setupTextAnalyzer() {
        var form = document.getElementById('text-analyzer-form');
        var fileInput = document.getElementById('text-file-input');
        var results = document.getElementById('text-analyzer-results');
        var fileName = document.getElementById('text-analyzer-file-name');
        var charCount = document.getElementById('text-analyzer-char-count');
        var letterTotal = document.getElementById('text-analyzer-letter-total');
        var packCount = document.getElementById('text-analyzer-pack-count');
        var limitingLetters = document.getElementById('text-analyzer-limiting-letters');
        var limitingRatio = document.getElementById('text-analyzer-limiting-ratio');
        var nutritionLabelPreview = document.getElementById('nutrition-label-preview');
        var jsonOutput = document.getElementById('text-analyzer-json');
        var letterGrid = document.getElementById('text-analyzer-grid');
        var magnetPack = window.MAGNET_LETTER_PACK;
        var nutritionData = window.CANNED_FOOD_NUTRITION;
        var zeroNutritionData;

        if (!form || !fileInput || !results || !fileName || !charCount || !letterTotal || !packCount || !limitingLetters || !limitingRatio || !nutritionLabelPreview || !jsonOutput || !magnetPack || !magnetPack.counts || !nutritionData) {
            return;
        }

        zeroNutritionData = buildDisplayNutritionData(nutritionData, 0);
        nutritionLabelPreview.innerHTML = renderNutritionLabel(zeroNutritionData);

        form.addEventListener('submit', function(event) {
            var selectedFile = fileInput.files && fileInput.files[0];

            event.preventDefault();
            results.hidden = true;

            if (!selectedFile) {
                setAnalyzerStatus('Select a text file before running the analysis.', true);
                return;
            }

            if (selectedFile.type !== 'text/plain') {
                setAnalyzerStatus('This prototype only accepts files with the MIME type text/plain.', true);
                return;
            }

            setAnalyzerStatus('Analyzing file in your browser...', false);

            selectedFile.text().then(function(textContent) {
                var letterCounts = countEnglishLetters(textContent);
                var packAnalysis = analyzePackRequirements(letterCounts, magnetPack.counts);
                var scaledNutritionData = buildDisplayNutritionData(nutritionData, packAnalysis.packsNeeded);

                fileName.textContent = selectedFile.name;
                charCount.textContent = textContent.length.toLocaleString();
                letterTotal.textContent = sumLetterCounts(letterCounts).toLocaleString();
                packCount.textContent = packAnalysis.packsNeeded.toLocaleString();
                limitingLetters.textContent = packAnalysis.limitingLetters.length ? packAnalysis.limitingLetters.map(function(item) {
                    return item.letter.toUpperCase();
                }).join(', ') : 'None';
                limitingRatio.textContent = packAnalysis.maxRatio.toFixed(2) + 'x';
                nutritionLabelPreview.innerHTML = renderNutritionLabel(scaledNutritionData);
                jsonOutput.textContent = JSON.stringify(letterCounts, null, 2);
                if (letterGrid) {
                    letterGrid.innerHTML = renderLetterGrid(packAnalysis);
                }
                results.hidden = false;

                setAnalyzerStatus('Analysis complete. The counts, pack estimate, and nutrition totals were generated entirely in your browser.', false);
            }).catch(function() {
                setAnalyzerStatus('The file could not be read. Please try another text file.', true);
            });
        });
    }

    setupTextAnalyzer();

})(jQuery);
