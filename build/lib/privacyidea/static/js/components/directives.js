/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-01-11 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
myApp.directive('tokenDataEdit', function(AuthFactory, instanceUrl) {
    return {
        scope: {
            text: '@',
            buttonText: '@',
            tokenData: '@',
            tokenKey: '@',
            inputPattern: '@',
            inputType: '@',
            callback: '&',
            callbackCancel: '&'
        },
        templateUrl: instanceUrl + "/static/views/directive.tokendata.html",
        link: function(scope, element, attr, ctrl) {
            scope.loggedInUser = AuthFactory.getUser();
            console.log("tokenDataEdit");
            console.log(scope.loggedInUser);
        }
    }
});

myApp.directive("piFilter", function (instanceUrl) {
    return {
        require: 'ngModel',
        restrict: 'E',
        scope: {},
        templateUrl: instanceUrl + "/static/views/directive.filter.table.html",
        link: function (scope, element, attr, ctrl) {
            scope.updateFilter = function() {
                ctrl.$setViewValue(scope.filterValue);
            };
            ctrl.$viewChangeListeners.push(function(){
              scope.$eval(attr.ngChange);
            });
        }
    }
});

myApp.directive("piSortBy", function(){
    return {
        restrict: 'A',
        link: function(scope, element, attr) {
            element.on('click', function() {
                column = attr.piSortBy;
                scope.params.sortby=column;
                scope.reverse=!scope.reverse;
                $(".sortUp").addClass("unsorted");
                $(".sortDown").addClass("unsorted");
                $(".sortUp").removeClass("sortUp");
                $(".sortDown").removeClass("sortDown");
                element.removeClass("unsorted");
                if (scope.reverse) {
                    element.addClass("sortDown");
                } else {
                    element.addClass("sortUp");
                }
                scope.getTokens();
            });
        }
    }
});


myApp.directive('assignUser', function($http, userUrl, AuthFactory, instanceUrl) {
    /*
    This directive is used to select a user from a realm

    newUserObject consists of .user and .realm
     */
    return {
        scope: {
            newUserObject: '=',
            realms: '='
        },
        templateUrl: instanceUrl + "/static/views/directive.assignuser.html",
        link: function (scope, element, attr) {
            console.log("Entering assignUser directive");
            console.log(scope.realms);
            console.log(scope.newUserObject);
            scope.loadUsers = function($viewValue) {
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: userUrl + "?username=*" + $viewValue + "*" +
                    "&realm=" + scope.newUserObject.realm,
                headers: {'Authorization': auth_token}
            }).then(function ($response) {
                return $response.data.result.value.map(function (item) {
                    return "[" + item.userid + "] " + item.username +
                        " (" + item.givenname + " " + item.surname + ")"
                });
            });
            };
        }
    }
});

myApp.directive('assignToken', function($http, tokenUrl,
                                        AuthFactory, instanceUrl) {
    /*
    This directive is used to select a serial number and assign it
    to the user.

    newTokenObject consists of .serial and .pin
     */
    return {
        scope: {
            newTokenObject: '='
        },
        templateUrl: instanceUrl + "/static/views/directive.assigntoken.html",
        link: function (scope, element, attr) {
            scope.loadSerials = function($viewValue) {
            var auth_token = AuthFactory.getAuthToken();
            return $http({
                method: 'GET',
                url: tokenUrl,
                headers: {'Authorization': auth_token},
                params: {assigned: "False",
                serial: "*" + $viewValue + "*"}
            }).then(function ($response) {
                return $response.data.result.value.tokens.map(function (item) {
                    return item.serial + " (" + item.tokentype + ")";
                });
            });
            };
        }
    }
});


myApp.directive('equals', function() {
  return {
    restrict: 'A', // only activate on element attribute
    require: '?ngModel', // get a hold of NgModelController
    link: function(scope, elem, attrs, ngModel) {
      if(!ngModel) return; // do nothing if no ng-model

      // watch own value and re-validate on change
      scope.$watch(attrs.ngModel, function() {
        validate();
      });

      // observe the other value and re-validate on change
      attrs.$observe('equals', function (val) {
        validate();
      });

      var validate = function() {
        // values
        var val1 = ngModel.$viewValue;
        var val2 = attrs.equals;

        // set validity
        ngModel.$setValidity('equals', ! val1 || ! val2 || val1 === val2);
      };
    }
  }
});

myApp.directive('statusClass', function() {
    return {
        link: function (scope, element, attrs, ngModel) {
            if (["OK", "1", 1].indexOf( attrs.statusClass )>-1) {
                element.addClass("label label-success");
                element.removeClass("label-danger");
            } else {
                element.addClass("label label-danger");
                element.removeClass("label-success");
            }
        }
    };
});
