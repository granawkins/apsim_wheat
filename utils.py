def interpolate(ref_x, ref_y, out_x):
    # If out of range, return outer y value
    if out_x < ref_x[0]:
        return ref_y[0]
    elif out_x > ref_x[-1]:
        return ref_y[-1]

    # Else, find the range that the value is within
    for i, x in enumerate(ref_x):
        next_x = ref_x[i+1]
        if out_x > next_x:
            continue

        # Interpolate with y = mx + b
        b = ref_y[i]
        next_y = ref_y[i+1]
        dy = next_y - b
        dx = next_x - x
        m = dy / dx
        return m * (out_x - x) + b
