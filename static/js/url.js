/*
    Copyright 2014 UW Information Technology, University of Washington

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Changes:

    =================================================================

*/
(function(){

    window.spacescout_url = window.spacescout_url || {

        load: function (path) {
            this.dispatch(this.parse_path(path));
        },

        dispatch: function (state) {
            if (!state) {
                state = this.parse_path(window.location.pathname);
            }

            if (window.default_location != state.campus
                || this.encode_current_search() != state.search) {
                $('#location_select option').each(function (i) {
                    var location = $(this).val().split(',');
                    if (location[2] == state.campus) {
                        window.default_latitude = location[0];
                        window.default_longitude = location[1];
                        window.default_location = location[2];
                        window.default_zoom = parseInt(location[3]);
                        $(this).attr('selected', 'selected');
                    }
                });
                
                repopulate_filters(this.decode_search_terms(state.search));
                run_custom_search();
            } else if (state.id) {
                data_loaded();
            } else if ($('.space-detail-container').length) {
                closeSpaceDetails();
            }
        },

        push: function (id) {
            var url = [''],
                campus = window.default_location,
                search = this.encode_current_search();

            url.push(campus);

            if (search && search.length) {
                url.push(search);
            }

            if (id) {
                url.push(id);
            }

            history.pushState({ campus: campus, search: search, id: id },
                              null,
                              url.join('/'));
        },

        replace: function (id) {
            var url = [''],
                campus = window.default_location,
                search = this.encode_current_search();

            url.push(campus);

            if (search && search.length) {
                url.push(search);
            }

            if (id) {
                url.push(id);
            }

            history.replaceState({ campus: campus, search: search, id: id },
                                 null,
                                 url.join('/'));
        },

        space_id: function (url) {
            var o = this.parse_path(url);

            return o ? o.id : null;
        },

        parse_path: function (path) {
            var state = {},
                m = path.match(/^\/([a-zA-Z]+)(\/([a-z][^/]*))?((\/(\d*))?(\/.+)?)?$/);

            if (m) {
                state['campus'] = m[1];
                state['search'] = m[3];
                state['id'] = (m[6] && m[6].length) ? parseInt(m[6]) : undefined;
            }

            return state;
        },

        encode_current_search: function () {
            return this.encode_search_terms(window.spacescout_search_options);
        },

        encode_search_terms: function (opts) {
            var terms = [], a, s;

            if (opts) {
                if (opts.hasOwnProperty('type')) {
                    a = [];

                    $.each(opts["type"], function () {
                        a.push(this);
                    });

                    if (a.length) {
                        terms.push('type:' + a.join(','));
                    }
                }

                if (opts["extended_info:reservable"]) {
                    terms.push('reservable');
                }

                terms.push('cap:' + opts["capacity"]);

                if (opts["open_at"]) {
                    terms.push('open:' + JSON.stringify(opts["open_at"]));
                }

                if (opts["open_until"]) {
                    terms.push('close:' + JSON.stringify(opts["open_until"]));
                }

                if (opts["building_name"]) {
                    terms.push('bld:' + opts["building_name"]);
                }

                // set resources
                if (opts["extended_info:has_whiteboards"]) {
                    terms.push('rwb');
                }
                if (opts["extended_info:has_outlets"]) {
                    terms.push('rol');
                }
                if (opts["extended_info:has_computers"]) {
                    terms.push('rcp');
                }
                if (opts["extended_info:has_scanner"]) {
                    terms.push('rsc');
                }
                if (opts["extended_info:has_projector"]) {
                    terms.push('rpj');
                }
                if (opts["extended_info:has_printing"]) {
                    terms.push('rpr');
                }
                if (opts["extended_info:has_displays"]) {
                    terms.push('rds');
                }

                // set noise level
                if (opts.hasOwnProperty("extended_info:noise_level")) {
                    a = [];

                    $.each(opts["extended_info:noise_level"], function () {
                        a.push(this);
                    });

                    if (a.length) {
                        terms.push('noise:' + a.join(','));
                    }
                }

                // set lighting
                if (opts["extended_info:has_natural_light"]) {
                    terms.push('natl');
                }

                // set food/coffee
                if (opts.hasOwnProperty("extended_info:food_nearby")) {
                    a = [];

                    $.each(opts["extended_info:food_nearby"], function () {
                        a.push(this);
                    });

                    if (a.length) {
                        terms.push('food:' + a.join(','));
                    }
                }
            }

            return (terms.length) ? terms.join('|') : null;
        },

        decode_search_terms: function (raw) {
            var opts = {},
                terms = raw ? raw.split('|') : [],
                term, v, a;

            $.each(terms, function () {
                a = this.split(':');
                v = a[1];
                switch (a[0]) {
                case 'type':
                    opts['type'] = [];
                    $.each(v.split(','), function () {
                        opts['type'].push(this);
                    });

                    break;
                case 'reservable':
                    opts["extended_info:reservable"] = true;
                    break;
                case 'cap':
                    opts["capacity"] = v;
                    break;
                case 'open':
                    opts["open_at"] = JSON.parse(v);
                    break;
                case 'close' :
                    opts["open_until"] = JSON.parse(v);
                    break;
                case 'bld' :
                    opts["building_name"] = v;
                    break;
                case 'rwb' :
                    opts["extended_info:has_whiteboards"] = true;
                    break;
                case 'rol' :
                    opts["extended_info:has_outlets"] = true;
                    break;
                case 'rcp' :
                    opts["extended_info:has_computers"] = true;
                    break;
                case 'rsc' :
                    opts["extended_info:has_scanner"] = true;
                    break;
                case 'rpj' :
                    opts["extended_info:has_projector"] = true;
                    break;
                case 'rpr' :
                    opts["extended_info:has_printing"] = true;
                    break;
                case 'rds' :
                    opts["extended_info:has_displays"] = true;
                    break;
                case 'natl' :
                    opts["extended_info:has_natural_light"] = true;
                    break;
                case 'noise' :
                    opts["extended_info:noise_level"] = [];
                    $.each(v.split(','), function () {
                        opts["extended_info:noise_level"].push(this);
                    });

                    break;
                case 'food' :
                    opts["extended_info:food_nearby"] = [];
                    $.each(v.split(','), function () {
                        opts["extended_info:food_nearby"].push(this);
                    });

                    break;
                default:
                    break;
                }
            });

            return opts;
        }

    };

    $(window).bind('popstate', function (e) {
        window.spacescout_url.dispatch(e.originalEvent.state);
    });

    $(document).on('searchResultsLoaded', function () {
        var state = window.spacescout_url.parse_path(window.location.pathname);
        if (!state.hasOwnProperty('search')) {
            window.spacescout_url.replace();
        }
    });


})(this);