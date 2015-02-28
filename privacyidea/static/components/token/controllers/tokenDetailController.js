
myApp.controller("tokenDetailController", function ($scope,
                                                    TokenFactory, UserFactory,
                                                    $stateParams,
                                                    $state, $rootScope,
                                                    ValidateFactory,
                                                    AuthFactory,
                                                    ConfigFactory,
                                                    MachineFactory) {
    $scope.tokenSerial = $stateParams.tokenSerial;
    $scope.editCountWindow = false;
    $scope.selectedRealms = {};
    $scope.newUser = {user: "", realm: $scope.defaultRealm};
    $scope.loggedInUser = AuthFactory.getUser();
    $scope.machinesPerPage = 5;
    $scope.params = {page: 1};
    // scroll to the top of the page
    document.body.scrollTop = document.documentElement.scrollTop = 0;

    // define functions
    $scope.get = function () {
        TokenFactory.getTokenForSerial($scope.tokenSerial, function (data) {
            $scope.token = data.result.value.tokens[0];
        });
    };

    $scope.return_to = function () {
        // After deleting the token, we return here.
        // history.back();
        $state.go($rootScope.previousState.state,
            $rootScope.previousState.params);
    };

    $scope.unassign = function () {
        if ($scope.loggedInUser.role == 'user') {
            TokenFactory.unassign($scope.tokenSerial, $state.go('token.list'));
        } else {
            TokenFactory.unassign($scope.tokenSerial, $scope.get);
        }
    };

    $scope.enable = function () {
        TokenFactory.enable($scope.tokenSerial, $scope.get);
    };

    $scope.disable = function () {
        TokenFactory.disable($scope.tokenSerial, $scope.get);
    };

    $scope.set = function (key, value) {
        TokenFactory.set($scope.tokenSerial, key, value, $scope.get);
    };
    $scope.reset = function () {
        TokenFactory.reset($scope.tokenSerial, $scope.get);
    };

    $scope.startEditRealm = function () {
        // fill the selectedRealms with the realms of the token
        $scope.selectedRealms = {};
        $scope.editTokenRealm = true;
        angular.forEach($scope.token.realms, function (realmname, _index) {
            $scope.selectedRealms[realmname] = true;
        })
    };

    $scope.cancelEditRealm = function () {
        $scope.editTokenRealm = false;
        $scope.selectedRealms = {};
    };

    $scope.saveRealm = function () {
        console.log(Object.keys($scope.selectedRealms));
        TokenFactory.setrealm($scope.tokenSerial, Object.keys($scope.selectedRealms), $scope.get);
        $scope.cancelEditRealm();
    };

    $scope.assignUser = function () {
        TokenFactory.assign({
            serial: $scope.tokenSerial,
            user: fixUser($scope.newUser.user),
            realm: $scope.newUser.realm,
            pin: $scope.newUser.pin
        }, $scope.get);
    };

    $scope.delete = function () {
        TokenFactory.delete($scope.tokenSerial, $scope.return_to);
    };

    $scope.setPin = function () {
        TokenFactory.setpin($scope.tokenSerial, "otppin",
            $scope.pin1, function () {
                $scope.pin1 = "";
                $scope.pin2 = "";
            });
    };

    $scope.resyncToken = function () {
        TokenFactory.resync({
            serial: $scope.tokenSerial,
            otp1: $scope.otp1,
            otp2: $scope.otp2
        }, function (data) {
            $scope.otp1 = "";
            $scope.otp2 = "";
            $scope.resultResync = data.result.value;
            $scope.get();
        });
    };

    $scope.testOtp = function () {
        ValidateFactory.check({
            serial: $scope.tokenSerial,
            pass: $scope.testPassword
        }, function (data) {
            $scope.resultTestOtp  = {result:data.result.value,
                                     detail:data.detail.message};
            $scope.get();
        });
    };


    // initialize
    $scope.get();

    if ($scope.loggedInUser.role == "admin") {
        // If the user is admin, we can fetch all realms
        ConfigFactory.getRealms(function (data) {
                $scope.realms = data.result.value;
        });
    }
    // If the loggedInUser is only a user, we do not need the realm list,
    // as we do not assign a token
    // read the application definition from the server
    MachineFactory.getApplicationDefinition(function(data){
        $scope.Applications = data.result.value;
        var applications = [];
        for(var k in $scope.Applications) applications.push(k);
        $scope.formInit = { application: applications};
    });

    $scope.getMachines = function () {
        MachineFactory.getMachineTokens({serial: $scope.tokenSerial},
                function (data) {
                    machinelist = data.result.value;
                    console.log(machinelist);
                    $scope.machineCount = machinelist.length;
                    var start = ($scope.params.page - 1) * $scope.machinesPerPage;
                    var stop = start + $scope.machinesPerPage;
                    $scope.machinedata = machinelist.slice(start, stop);
                })
    };
    // Change the pagination
    $scope.pageChanged = function () {
        console.log('Page changed to: ' + $scope.params.page);
        $scope.getMachines();
    };

    $scope.detachMachineToken = function (machineid, resolver, application) {
        MachineFactory.detachTokenMachine({serial: $scope.tokenSerial,
                application: application,
                machineid: machineid,
                resolver: resolver
        }, function (data) {
            $scope.getMachines();
        });
    };

    $scope.getMachines();
});
