$fn = 50;

LENGTH=91.6;
WIDTH=68.1;
THICKNESS=5.9;
ROUNDED=3.0;
HOLE_DISTANCE=3.8;
HOLE_RADIUS=1.5;

PCB_LENGTH=28.2+0.8;
PCB_WIDTH=27.1+0.8;
PCB_THICKNESS=3.4;
SCREEN_LENGTH=26.6+0.8;
SCREEN_WIDTH=19.0+0.8;
SCREEN_X=(PCB_LENGTH-SCREEN_LENGTH)/2;
SCREEN_Y=4.2;
HEADER_LENGTH=11;
HEADER_WIDTH=3;
HEADER_X=(PCB_LENGTH-HEADER_LENGTH)/2;

module screen() {
    union() {
        linear_extrude(PCB_THICKNESS-1)
            square([PCB_LENGTH,PCB_WIDTH], false);
        linear_extrude(PCB_THICKNESS)
            translate([SCREEN_X,SCREEN_Y])
                square([SCREEN_LENGTH,SCREEN_WIDTH], false);
        translate([HEADER_X,0,-PCB_THICKNESS-1])
            linear_extrude(PCB_THICKNESS+1)
                square([HEADER_LENGTH,HEADER_WIDTH], false);
    }
}

module base(thickness) {
    linear_extrude(thickness)
    difference() {
        translate([ROUNDED,ROUNDED])
        minkowski() {
            square([LENGTH-ROUNDED*2, WIDTH-ROUNDED*2], false);
            circle(ROUNDED);
        }
        translate([HOLE_DISTANCE,HOLE_DISTANCE]) circle(HOLE_RADIUS);
        translate([LENGTH-HOLE_DISTANCE,HOLE_DISTANCE]) circle(HOLE_RADIUS);
        translate([HOLE_DISTANCE,WIDTH-HOLE_DISTANCE]) circle(HOLE_RADIUS);
        translate([LENGTH-HOLE_DISTANCE,WIDTH-HOLE_DISTANCE]) circle(HOLE_RADIUS);
    }
}

module top() {
    difference() {
        base(PCB_THICKNESS);
        translate([20,(WIDTH-PCB_LENGTH)/2]) translate([0,PCB_LENGTH]) rotate([0,0,-90]) screen();
    }
}

module bottom() {
    difference() {
        base(THICKNESS - PCB_THICKNESS);
        translate([20,(WIDTH-PCB_LENGTH)/2,PCB_THICKNESS]) 
        translate([0,PCB_LENGTH]) rotate([0,0,-90]) screen();
    }
}

rotate([180,0,0]) top();
//bottom();
