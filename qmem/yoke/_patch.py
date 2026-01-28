
import stim


def centroid(points):
    n = len(points)
    x = sum(p[0] for p in points) / n
    y = sum(p[1] for p in points) / n
    return (x, y)

class Qubit(object):

    def __init__(self, coord, id):
        super().__init__()
        self.coord = coord
        self.id = id
    

class DataQubit(Qubit):

    def __init__(self, coord, id):
        super().__init__(coord, id)
        self.ancilla = []
    
    def add_ancilla(self, ancilla_qubit):
        self.ancilla.append(ancilla_qubit)

    def __repr__(self):
        return f"Data Qubit {self.coord}"


class AncillaQubit(Qubit):

    def __init__(self, coord:tuple[int, int], id:int , stabilizer_type: str):
        super().__init__(coord, id)
        self.stabilizer_type = stabilizer_type

        self.order = ['NW', 'NE', 'SW', 'SE']
        self.data_qubits: dict[str, DataQubit] = {
            'NW': None,
            'NE': None,
            'SE': None,
            'SW': None
        }

    def add_associated_data_qubits(self, data_qubit:DataQubit):
        ax, ay = self.coord
        x, y = data_qubit.coord
        if x < ax and y > ay:
            self.data_qubits['NW'] = data_qubit
        if x > ax and y > ay:
            self.data_qubits['NE'] = data_qubit
        if x > ax and y < ay:
            self.data_qubits['SE'] = data_qubit
        if x < ax and y < ay:
            self.data_qubits['SW'] = data_qubit

    def stabilizer_measurement(self, direction:str):
        if self.data_qubits[direction] == None:
            return None
        
        if self.stabilizer_type == 'x':
            return self.id, self.data_qubits[direction].id
        else:
            return self.data_qubits[direction].id, self.id
        
    
    def pauli_string(self):
        qubits = []
        for direction in self.order:
            if self.data_qubits[direction] is not None:
                qubits.append(self.data_qubits[direction].id) 
        
        return self.stabilizer_type.capitalize(), qubits



class Patch(object):

    def __init__(self, diameter, coord_offset, qubit_offset):
        super().__init__()
        self.diameter = diameter
        self.size = 2*diameter**2 - 1
        self.data_qubits: dict[tuple[int, int], DataQubit] = {}
        self.ancilla_qubits: dict[str, list[AncillaQubit]] = {'X': [], 'Z': []}
        self.coord_offset = coord_offset
        self.qubit_offset = qubit_offset
        data_qubis_coords = []

        self._num_qubits = 0

        coord = (0, -2)
        self.data_qubits[coord] = DataQubit(coord, self._num_qubits)
        self._num_qubits += 1

        for i in range(diameter):
            for j in range(diameter):
                coord = (i, j)
                self.data_qubits[coord] = DataQubit(coord, self._num_qubits)
                data_qubis_coords.append((i, j))
                self._num_qubits += 1



        def x_stabilizers(i, j, direction):
            plaquette_coords = [(i, j), (i+1, j)]
            if direction:
                plaquette_coords.append((i, j-1))
                plaquette_coords.append((i+1, j-1))
            else:
                plaquette_coords.append((i, j+1))
                plaquette_coords.append((i+1, j+1))
            return plaquette_coords
        

        def z_stabilizers(i, j, direction):
            plaquette_coords = [(j, i), (j, i+1)]
            if direction:
                plaquette_coords.append((j+1, i))
                plaquette_coords.append((j+1, i+1))
            else:
                plaquette_coords.append((j-1, i))
                plaquette_coords.append((j-1, i+1))
            return plaquette_coords

        self._ancilla_association(0, diameter, 0, diameter, 'X', x_stabilizers)
        self._ancilla_association(0, diameter, 0, diameter, 'Z', z_stabilizers)

    def _ancilla_association(self, 
                            i_low, i_up, 
                            j_low, j_up,
                            stabilizer_type,
                            plaquette_coord_func):

        direction = True
        for i in range(i_low, i_up):
            for j in range(j_low, j_up, 2):
                if (i + 1)>= i_up:
                    break
                plaquette_coords = plaquette_coord_func(i, j, direction)
                ancilla_coord = centroid(plaquette_coords)

                ancilla = AncillaQubit(ancilla_coord, self._num_qubits, stabilizer_type)
                self.ancilla_qubits[stabilizer_type].append(ancilla) # append the reference

                self._num_qubits += 1

                for coord in plaquette_coords:
                    if coord in self.data_qubits:
                        ancilla.add_associated_data_qubits(self.data_qubits[coord]) 
                
            direction ^= True

    def set_physical_qubit_offset(self, offset):
        self._qubit_map = {}
        for i in range(self._num_qubits):
            self._qubit_map[i] = offset
            offset += 1


    def get_coordinates(self):

        coordinates = []
        for coord, qubit in self.data_qubits.items():
            coordinates.append(((coord[0] + self.coord_offset[0], coord[1] + self.coord_offset[1]), qubit.id + self.qubit_offset))


        ancilla = self.ancilla_qubits['X'] + self.ancilla_qubits['Z']
        for anc in ancilla:
                coord = anc.coord
                coordinates.append(((coord[0] + self.coord_offset[0], coord[1] + self.coord_offset[1]), anc.id + self.qubit_offset))

        return coordinates

    def ancilla_initialization(self):
        R = []
        Rx = []
        ancilla = self.ancilla_qubits['X'] + self.ancilla_qubits['Z']

        for anc in ancilla:
            if anc.stabilizer_type == 'X':
                Rx.append(anc.id + self.qubit_offset)
            else:
                R.append(anc.id + self.qubit_offset)
        
        return R, Rx
        
    def initial_stabilizer_measurement(self):
        pass

    def __make_obserevable(self, Stype:str, qubits: list[int]) ->str :
        ops = []
        for q in qubits:
            ops.append(f"{Stype}{q}") 

        return "*".join(ops)

    def x_observable(self) -> str:
        qs = [
            self.__id_trans(self.data_qubits[(0, 0)]), 
            self.__id_trans(self.data_qubits[(0, 1)]),
            self.__id_trans(self.data_qubits[(0, 2)]),
            self.__id_trans(self.data_qubits[(0, -2)]) # magical ancilla
        ]

        return self.__make_obserevable("X", qs)

    def z_observable(self):
        qs = [
            self.__id_trans(self.data_qubits[(0, 0)]), 
            self.__id_trans(self.data_qubits[(1, 0)]),
            self.__id_trans(self.data_qubits[(2, 0)]),
            self.__id_trans(self.data_qubits[(0, -2)]) # magical ancilla
        ]

        return self.__make_obserevable('Z', qs)

    def __sorted_ancilla(self):
        """
        Docstring for __sorted_ancilla
        
        :param self: Description
        """
        ancilla = self.ancilla_qubits['X'] + self.ancilla_qubits['Z']
        return sorted(ancilla, key=lambda c: (c.coord[0], c.coord[1]))        

    def pauli_strings(self):
        ancilla = self.__sorted_ancilla()
        strings = []
        for q in ancilla:
            _type, _qubits_id = q.pauli_string()
            strings.append(f'{'*'.join([_type + str(_id + self.qubit_offset) for _id in _qubits_id])}')

        return strings
    
    def __id_trans(self, qubit: Qubit):
        return qubit.id + self.qubit_offset 

    def __coord_trans(self, qubit: Qubit):
        return (qubit.coord[0] + self.coord_offset[0], qubit.coord[1] + self.coord_offset[1])
    
    def syndrome_extraction(self, direction):
        ancilla = self.ancilla_qubits['X'] + self.ancilla_qubits['Z']
        CNOT = []
        for anc in ancilla:

            if anc.data_qubits[direction] != None:
                order = [self.__id_trans(anc), self.__id_trans(anc.data_qubits[direction])]
                if anc.stabilizer_type == 'X':
                    CNOT += order
                else:
                    order.reverse()
                    CNOT += order
        
        return CNOT

    
    def measurement(self):
        ancilla = self.__sorted_ancilla()
        mes = []
        for anc in ancilla:
            mes.append((anc.stabilizer_type, (self.__id_trans(anc), self.__coord_trans(anc))))

        # M = [(self.__id_trans(anc), self.__coord_trans(anc)) for anc in self.ancilla_qubits['Z']]
        # Mx = [(self.__id_trans(anc), self.__coord_trans(anc)) for anc in self.ancilla_qubits['X']]

        return mes


class YokedSurfaceCode(object):

    def __init__(self,
                 num_patches,
                 patch_diameter, 
                 noise_level,
                 rounds,
                 ):
        super().__init__()

        self.patch_diameter = patch_diameter
        self.patches: list[Patch] = []
        self.num_qubits = 0
        self.noise_level = noise_level
        self.rounds = rounds

        coord_offset = 0
        for p in range(num_patches):
            patch = Patch(self.patch_diameter, (coord_offset, 0), self.num_qubits)
            patch.set_physical_qubit_offset(self.num_qubits)
            self.patches.append(patch)
            self.num_qubits += patch._num_qubits
            coord_offset += 4


    def _patch_to_stim_circuit(self, ) -> stim.Circuit:

        pass

    def circuit_initialization(self) -> stim.Circuit:

        pass


    def decoding_circuit(self):
        pass

    def to_stim_circuit(self) -> stim.Circuit:
        circ = stim.Circuit()

        for patch in self.patches:
            coords = patch.get_coordinates()
            for coord, num in coords:
                print(coord, num)
                circ.append(stim.CircuitInstruction("QUBIT_COORDS", [num], list(coord)))

        # measure X obersevables 
        obs_count = 0
        for patch in self.patches:
            x = patch.x_observable()
            circ.append("MPP", stim.PauliString(x)) 
            circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], [obs_count])
            obs_count += 1
        
        # measure Z observebles
        for patch in self.patches:
            z = patch.z_observable()
            circ.append("MPP", stim.PauliString(z)) 
            circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], [obs_count])
            obs_count += 1
        # circ.append("TICK")
        
        for patch in self.patches:
            pauli_strings = patch.pauli_strings()
            for ps in pauli_strings:
                circ.append("MPP", stim.PauliString(ps))

        circ.append("TICK") 
        # return circ


        # ------------- repeat block ---------------
        repeat_block = stim.Circuit()
        for patch in self.patches:
            R, Rx = patch.ancilla_initialization()
            for r_id, rx_id in zip(R, Rx):
                repeat_block.append(stim.CircuitInstruction("R", [r_id])) 
                repeat_block.append(stim.CircuitInstruction("Rx", [rx_id])) 
        repeat_block.append("TICK")
        
        # syndrome extraction
        for direction in ['NW', 'NE', 'SE', 'SW']:
            for patch in self.patches:
                repeat_block.append(
                    stim.CircuitInstruction("CNOT", patch.syndrome_extraction(direction))
                )
        
            repeat_block.append(stim.CircuitInstruction("TICK"))

        # measurement

        measurement_coords = []
        for patch in self.patches:
            meas = patch.measurement()
            for _type, (m, c) in meas:
                if _type == "X":
                    mes_type = "MX"
                else:
                    mes_type = "M"
                repeat_block.append(stim.CircuitInstruction(mes_type, [m]))
                measurement_coords.append(c)

            # for m, c in Mx:
            #     repeat_block.append(stim.CircuitInstruction("MX", [m]))
            #     measurement_coords.append(c)
            # for m, c in M:
            #     repeat_block.append(stim.CircuitInstruction("M", [m]))
            #     measurement_coords.append(c)

        # detectors
        print(len(measurement_coords))
        rec = -len(measurement_coords)
        prev = - 2*len(measurement_coords)
        for c in measurement_coords:
            repeat_block.append(stim.CircuitInstruction("DETECTOR", targets=[stim.target_rec(rec), stim.target_rec(prev)], gate_args=[c[0], c[1], 0]))
            rec += 1
            prev += 1

        repeat_block.append(stim.CircuitInstruction("TICK"))
        circ.append(stim.CircuitRepeatBlock(self.rounds, repeat_block))
        # -------------Repeat block ends --------------------


        # stabilizer measurement
        for patch in self.patches:
            pauli_strings = patch.pauli_strings()
            for ps in pauli_strings:
                circ.append("MPP", stim.PauliString(ps))


        # final round detectors
        rec = -len(measurement_coords)
        prev = - 2*len(measurement_coords)
        for c in measurement_coords:
            circ.append(stim.CircuitInstruction("DETECTOR", targets=[stim.target_rec(rec), stim.target_rec(prev)], gate_args=[c[0], c[1], 0]))
            rec += 1
            prev += 1

        for patch in self.patches:
            x = patch.x_observable()
            circ.append("MPP", stim.PauliString(x)) 
            circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], [obs_count])
            obs_count += 1
        
        # measure Z observebles
        for patch in self.patches:
            z = patch.z_observable()
            circ.append("MPP", stim.PauliString(z)) 
            circ.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], [obs_count])
            obs_count += 1
        circ.append("TICK")    
        

        # 1D yoke surface code 
        starting_index = -len(self.patches)*2 - (self.rounds + 2) * (len(measurement_coords)) - len(self.patches) - 1
        recs = []
        for i in range(len(self.patches)*2):
            recs.append(-i - 1)
            recs.append(starting_index + i)

        print(recs) 
        circ.append("DETECTOR", targets=[stim.target_rec(rec) for rec in recs])
        return circ 
    

def outputSvg(diag, filename):
    with open(filename, 'w') as file:
        file.write(str(diag))
        file.close()



if __name__ == "__main__":

    # patch = Patch(3, (0, 0), 0)

    # print(patch.pauli_strings())

    ysc = YokedSurfaceCode(1, 3, 0.001, 1)
    circ = ysc.to_stim_circuit()

    print("Circuit:")
    print(circ)
    print("End of the circuit")

    # circ = stim.Circuit.generated(
    #     "surface_code:rotated_memory_x",
    #     rounds=1,
    #     distance=3,
    #     before_measure_flip_probability=0.01,
    #     before_round_data_depolarization=0.02,
    # )

    outputSvg(circ.diagram('detslice-with-ops-svg'), 'detslice-with-ops-svg.svg')
    outputSvg(circ.diagram('timeline-svg'), 'timeline-svg.svg' )

    # construct the stim circuit for the patch



    dem = circ.detector_error_model()
    print(repr(dem))

    # print(circ.diagram('detslice-with-ops-svg', tick=range(3, 13), filter_coords=['D32', 'L3', ]))

    # for key in patch.ancilla_qubits:
    #     print(patch.ancilla_qubits[key].stabilizer_type, patch.ancilla_qubits[key].coord)